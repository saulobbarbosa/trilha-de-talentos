from __future__ import annotations

from datetime import date as date_type
from datetime import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_roles
from app.models import OutboxEmail, Reservation, ReservationStatus, Role, Training, TrainingStatus, User, utcnow
from app.security import client_ip, generate_temp_password, hash_password
from app.services.audit import log_action
from app.services.email import (
    queue_account_created_email,
    queue_password_reset_email,
    queue_training_cancelled_email,
    site_url,
)
from app.services.training_views import active_reservation_counts, training_payload

router = APIRouter(prefix="/api/rh", tags=["rh"])
settings = get_settings()


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("Informe um e-mail válido.")
    return value


def _normalize_name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 3:
        raise ValueError("Informe o nome completo da pessoa.")
    return value


class PersonCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    email: str = Field(min_length=5, max_length=255)
    role: Role
    leader_id: int | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return _normalize_name(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _normalize_email(value)


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=160)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    role: Role | None = None
    leader_id: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return _normalize_name(value) if value is not None else None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _normalize_email(value) if value is not None else None


class TrainingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    instructor_id: int
    date: date_type
    start_time: str
    end_time: str
    location: str = Field(min_length=2, max_length=200)
    seats: int = Field(ge=1, le=500)
    workload_hours: float = Field(default=8, gt=0, le=100)

    @field_validator("title", "location")
    @classmethod
    def _trim(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return value.strip()


class TrainingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    instructor_id: int | None = None
    date: date_type | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = Field(default=None, min_length=2, max_length=200)
    seats: int | None = Field(default=None, ge=1, le=500)
    workload_hours: float | None = Field(default=None, gt=0, le=100)

    @field_validator("title", "location")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CancelTrainingRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None


def _person_payload(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "leader_id": user.leader_id,
        "leader_name": user.leader.name if user.leader else None,
        "must_change_password": user.must_change_password,
        "face_enrolled": user.face_enrolled,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat(),
    }


def _active_leaders(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role == Role.LIDER.value, User.is_active.is_(True))
            .order_by(User.name)
        ).all()
    )


def _active_instructors(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role == Role.INSTRUTOR.value, User.is_active.is_(True))
            .order_by(User.name)
        ).all()
    )


def _validate_leader(db: Session, leader_id: int | None, *, person_id: int | None = None) -> None:
    if leader_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione o líder responsável pelo funcionário.",
        )
    if person_id is not None and leader_id == person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma pessoa não pode ser líder de si mesma.",
        )
    leader = db.get(User, leader_id)
    if not leader or leader.role != Role.LIDER.value or not leader.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O líder selecionado não está ativo ou não possui esse perfil.",
        )


def _ensure_email_available(db: Session, email: str, *, ignore_user_id: int | None = None) -> None:
    statement = select(User).where(User.email == email)
    if ignore_user_id is not None:
        statement = statement.where(User.id != ignore_user_id)
    if db.scalar(statement):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma pessoa cadastrada com este e-mail.",
        )


def _validate_instructor(db: Session, instructor_id: int) -> User:
    instructor = db.get(User, instructor_id)
    if not instructor or instructor.role != Role.INSTRUTOR.value or not instructor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione um instrutor ativo.",
        )
    return instructor


def _parse_time(value: str, field_name: str) -> time:
    try:
        hours, minutes = value.strip().split(":")[:2]
        return time(hour=int(hours), minute=int(minutes))
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Informe um horário válido para {field_name}.",
        )


def _validate_schedule(training_date: date_type, start_time, end_time) -> None:
    if training_date < date_type.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data do treinamento não pode estar no passado.",
        )
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O horário de término deve ser posterior ao horário de início.",
        )


@router.get("/options")
def options(
    _: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "leaders": [
            {"id": leader.id, "name": leader.name, "email": leader.email}
            for leader in _active_leaders(db)
        ],
        "instructors": [
            {"id": instructor.id, "name": instructor.name, "email": instructor.email}
            for instructor in _active_instructors(db)
        ],
    }


@router.get("/people")
def list_people(
    _: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    people = db.scalars(select(User).order_by(User.is_active.desc(), User.name)).all()
    return {
        "people": [_person_payload(person) for person in people],
        "total": len(people),
        "active": sum(1 for person in people if person.is_active),
    }


@router.post("/people", status_code=status.HTTP_201_CREATED)
def create_person(
    payload: PersonCreate,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_email_available(db, payload.email)
    role = payload.role.value
    leader_id = payload.leader_id
    if role == Role.FUNCIONARIO.value:
        _validate_leader(db, leader_id)
    else:
        leader_id = None

    temporary_password = generate_temp_password()
    person = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(temporary_password),
        role=role,
        leader_id=leader_id,
        must_change_password=True,
        face_enrolled=False,
        is_active=True,
    )
    db.add(person)
    db.flush()
    queue_account_created_email(
        db,
        user=person,
        temporary_password=temporary_password,
        base_url=site_url(request),
    )
    log_action(
        db,
        actor_id=actor.id,
        action="pessoa_criada",
        entity="user",
        entity_id=person.id,
        details={"role": role, "leader_id": leader_id},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(person)
    return {"person": _person_payload(person), "temporary_password": temporary_password}


@router.patch("/people/{person_id}")
def update_person(
    person_id: int,
    payload: PersonUpdate,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    person = db.get(User, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada.")

    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields and fields["name"] is not None:
        person.name = fields["name"]
    if "email" in fields and fields["email"] is not None:
        _ensure_email_available(db, fields["email"], ignore_user_id=person.id)
        person.email = fields["email"]

    new_role = fields.get("role")
    new_role_value = new_role.value if isinstance(new_role, Role) else person.role
    role_changing = new_role_value != person.role
    active_reservations = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.employee_id == person.id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
    ) or 0

    if role_changing:
        team_count = db.scalar(
            select(func.count(User.id)).where(
                User.leader_id == person.id,
                User.is_active.is_(True),
            )
        ) or 0
        if person.role == Role.LIDER.value and team_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reatribua os integrantes da equipe antes de alterar o perfil deste líder.",
            )
        if person.role == Role.INSTRUTOR.value:
            training_count = db.scalar(
                select(func.count(Training.id)).where(
                    Training.instructor_id == person.id,
                    Training.status.in_(
                        [TrainingStatus.AGENDADO.value, TrainingStatus.EM_ANDAMENTO.value]
                    ),
                )
            ) or 0
            if training_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reatribua as turmas ativas antes de alterar o perfil deste instrutor.",
                )
        if active_reservations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancele as reservas ativas desta pessoa antes de alterar o perfil.",
            )
        person.role = new_role_value

    if "leader_id" in fields or role_changing:
        leader_id = fields.get("leader_id", person.leader_id)
        if person.role == Role.FUNCIONARIO.value:
            _validate_leader(db, leader_id, person_id=person.id)
            person.leader_id = leader_id
        else:
            person.leader_id = None

    if "is_active" in fields and fields["is_active"] is not None:
        activating = bool(fields["is_active"])
        if not activating:
            if person.id == actor.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Você não pode desativar a própria conta.",
                )
            if person.role == Role.RH.value:
                other_rh = db.scalar(
                    select(func.count(User.id)).where(
                        User.role == Role.RH.value,
                        User.is_active.is_(True),
                        User.id != person.id,
                    )
                ) or 0
                if other_rh == 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Mantenha pelo menos um usuário de RH ativo.",
                    )
            team_count = db.scalar(
                select(func.count(User.id)).where(
                    User.leader_id == person.id,
                    User.is_active.is_(True),
                )
            ) or 0
            if team_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reatribua os integrantes da equipe antes de desativar este líder.",
                )
            if active_reservations:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cancele as reservas ativas desta pessoa antes de desativá-la.",
                )
            if person.role == Role.INSTRUTOR.value:
                training_count = db.scalar(
                    select(func.count(Training.id)).where(
                        Training.instructor_id == person.id,
                        Training.status.in_(
                            [TrainingStatus.AGENDADO.value, TrainingStatus.EM_ANDAMENTO.value]
                        ),
                    )
                ) or 0
                if training_count:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Reatribua as turmas ativas antes de desativar este instrutor.",
                    )
        person.is_active = activating

    log_action(
        db,
        actor_id=actor.id,
        action="pessoa_atualizada",
        entity="user",
        entity_id=person.id,
        details={"fields": list(fields)},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(person)
    return {"person": _person_payload(person)}


@router.post("/people/{person_id}/reset-password")
def reset_person_password(
    person_id: int,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    person = db.get(User, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada.")
    if person.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use a alteração de senha da sua própria conta.",
        )
    if not person.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ative a pessoa antes de redefinir a senha.",
        )

    temporary_password = generate_temp_password()
    person.password_hash = hash_password(temporary_password)
    person.must_change_password = True
    queue_password_reset_email(
        db,
        user=person,
        temporary_password=temporary_password,
        base_url=site_url(request),
    )
    log_action(
        db,
        actor_id=actor.id,
        action="senha_redefinida",
        entity="user",
        entity_id=person.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return {"ok": True, "temporary_password": temporary_password}


@router.get("/trainings")
def list_trainings(
    _: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    trainings = db.scalars(
        select(Training).order_by(Training.date.desc(), Training.start_time.desc())
    ).all()
    reserved = active_reservation_counts(db, [training.id for training in trainings])
    return {"trainings": [training_payload(db, item, reserved.get(item.id, 0)) for item in trainings]}


@router.post("/trainings", status_code=status.HTTP_201_CREATED)
def create_training(
    payload: TrainingCreate,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    _validate_instructor(db, payload.instructor_id)
    start_time = _parse_time(payload.start_time, "início")
    end_time = _parse_time(payload.end_time, "término")
    _validate_schedule(payload.date, start_time, end_time)

    training = Training(
        title=payload.title,
        description=payload.description,
        instructor_id=payload.instructor_id,
        date=payload.date,
        start_time=start_time,
        end_time=end_time,
        location=payload.location,
        seats=payload.seats,
        workload_hours=payload.workload_hours,
        status=TrainingStatus.AGENDADO.value,
        created_by_id=actor.id,
    )
    db.add(training)
    db.flush()
    log_action(
        db,
        actor_id=actor.id,
        action="treinamento_criado",
        entity="training",
        entity_id=training.id,
        details={"title": training.title, "date": training.date.isoformat()},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(training)
    return {"training": training_payload(db, training, 0)}


@router.patch("/trainings/{training_id}")
def update_training(
    training_id: int,
    payload: TrainingUpdate,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    training = db.get(Training, training_id)
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
    if training.status != TrainingStatus.AGENDADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Somente treinamentos agendados podem ser editados.",
        )

    fields = payload.model_dump(exclude_unset=True)
    if "instructor_id" in fields and fields["instructor_id"] is not None:
        _validate_instructor(db, fields["instructor_id"])
        training.instructor_id = fields["instructor_id"]
    if "title" in fields and fields["title"] is not None:
        training.title = fields["title"]
    if "description" in fields and fields["description"] is not None:
        training.description = fields["description"]
    if "location" in fields and fields["location"] is not None:
        training.location = fields["location"]
    if "workload_hours" in fields and fields["workload_hours"] is not None:
        training.workload_hours = fields["workload_hours"]

    start_time = (
        _parse_time(fields["start_time"], "início")
        if fields.get("start_time") is not None
        else training.start_time
    )
    end_time = (
        _parse_time(fields["end_time"], "término")
        if fields.get("end_time") is not None
        else training.end_time
    )
    training_date = fields.get("date") or training.date
    _validate_schedule(training_date, start_time, end_time)

    reserved = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.training_id == training.id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
    ) or 0
    seats = fields.get("seats", training.seats)
    if seats is not None and seats < reserved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O treinamento já possui {reserved} reservas ativas. Ajuste as vagas para pelo menos esse valor.",
        )

    training.date = training_date
    training.start_time = start_time
    training.end_time = end_time
    if seats is not None:
        training.seats = seats

    log_action(
        db,
        actor_id=actor.id,
        action="treinamento_atualizado",
        entity="training",
        entity_id=training.id,
        details={"fields": list(fields)},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(training)
    return {"training": training_payload(db, training, reserved)}


@router.post("/trainings/{training_id}/cancel")
def cancel_training(
    training_id: int,
    request: Request,
    payload: CancelTrainingRequest | None = None,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    training = db.get(Training, training_id)
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
    if training.status != TrainingStatus.AGENDADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Somente treinamentos agendados podem ser cancelados.",
        )

    reason = payload.reason if payload else None
    rows = db.execute(
        select(Reservation, User)
        .join(User, User.id == Reservation.employee_id)
        .where(
            Reservation.training_id == training.id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
    ).all()
    cancelled_at = utcnow()
    for reservation, employee in rows:
        reservation.status = ReservationStatus.CANCELADA.value
        reservation.cancelled_at = cancelled_at
        queue_training_cancelled_email(
            db,
            user=employee,
            training=training,
            reason=reason,
        )

    training.status = TrainingStatus.CANCELADO.value
    log_action(
        db,
        actor_id=actor.id,
        action="treinamento_cancelado",
        entity="training",
        entity_id=training.id,
        details={"reason": reason, "cancelled_reservations": len(rows)},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(training)
    return {
        "ok": True,
        "cancelled_reservations": len(rows),
        "training": training_payload(db, training, 0),
    }


@router.delete("/trainings/{training_id}")
def delete_training(
    training_id: int,
    request: Request,
    actor: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    training = db.get(Training, training_id)
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
    payload = training_payload(db, training)
    if not payload["can_delete"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este treinamento possui histórico de reservas ou presenças. Cancele-o em vez de excluir.",
        )

    log_action(
        db,
        actor_id=actor.id,
        action="treinamento_excluido",
        entity="training",
        entity_id=training.id,
        details={"title": training.title},
        ip_address=client_ip(request),
    )
    db.delete(training)
    db.commit()
    return {"ok": True}


@router.get("/outbox")
def list_outbox(
    _: User = Depends(require_roles(Role.RH)),
    db: Session = Depends(get_db),
) -> dict:
    emails = db.scalars(select(OutboxEmail).order_by(OutboxEmail.id.desc()).limit(60)).all()
    return {
        "emails": [
            {
                "id": email.id,
                "recipient": email.recipient,
                "subject": email.subject,
                "body": email.body,
                "created_at": email.created_at.isoformat(),
                "sent": email.sent,
                "error": email.error,
            }
            for email in emails
        ],
        "smtp_enabled": bool(settings.smtp_host.strip()),
        "dev_mode": settings.dev_mode,
    }
