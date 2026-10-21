from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Attendance,
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
    utcnow,
)
from app.security import client_ip
from app.services.audit import log_action
from app.services.email import (
    queue_reservation_cancelled_email,
    queue_reservation_confirmed_email,
    site_url,
)
from app.services.training_views import active_reservation_counts, training_payload

router = APIRouter(prefix="/api/leader", tags=["lider"])


class ReservationCreate(BaseModel):
    training_id: int
    employee_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("employee_ids")
    @classmethod
    def _unique(cls, value: list[int]) -> list[int]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("Selecione pelo menos um integrante do time.")
        return unique


def _team(db: Session, leader: User) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(
                User.leader_id == leader.id,
                User.role == Role.FUNCIONARIO.value,
                User.is_active.is_(True),
            )
            .order_by(User.name)
        ).all()
    )


@router.get("/reservations")
def list_reservations(
    leader: User = Depends(require_roles(Role.LIDER)),
    db: Session = Depends(get_db),
) -> dict:
    team = _team(db, leader)
    team_ids = [member.id for member in team]
    today = date_type.today()

    trainings = list(
        db.scalars(
            select(Training)
            .where(
                Training.status == TrainingStatus.AGENDADO.value,
                Training.date >= today,
            )
            .order_by(Training.date, Training.start_time)
        ).all()
    )
    reserved = active_reservation_counts(db, [training.id for training in trainings])
    team_reserved: dict[int, list[int]] = {}
    if trainings and team_ids:
        rows = db.execute(
            select(Reservation.training_id, Reservation.employee_id).where(
                Reservation.training_id.in_([training.id for training in trainings]),
                Reservation.employee_id.in_(team_ids),
                Reservation.status == ReservationStatus.ATIVA.value,
            )
        ).all()
        for training_id, employee_id in rows:
            team_reserved.setdefault(training_id, []).append(employee_id)

    trainings_payload = []
    for training in trainings:
        item = training_payload(db, training, reserved.get(training.id, 0))
        item["team_reserved_ids"] = sorted(team_reserved.get(training.id, []))
        trainings_payload.append(item)

    reservations_payload = []
    if team_ids:
        rows = db.execute(
            select(Reservation, Training, User)
            .join(Training, Training.id == Reservation.training_id)
            .join(User, User.id == Reservation.employee_id)
            .where(Reservation.employee_id.in_(team_ids))
            .order_by(Reservation.status.desc(), Training.date.desc(), Training.start_time.desc())
            .limit(100)
        ).all()
        for reservation, training, employee in rows:
            reservations_payload.append(
                {
                    "id": reservation.id,
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "training_id": training.id,
                    "title": training.title,
                    "date": training.date.isoformat(),
                    "start_time": training.start_time.strftime("%H:%M"),
                    "end_time": training.end_time.strftime("%H:%M"),
                    "location": training.location,
                    "instructor": training.instructor.name if training.instructor else "",
                    "training_status": training.status,
                    "status": reservation.status,
                    "created_at": reservation.created_at.isoformat(),
                    "cancelled_at": reservation.cancelled_at.isoformat()
                    if reservation.cancelled_at
                    else None,
                }
            )

    return {
        "team": [
            {
                "id": member.id,
                "name": member.name,
                "email": member.email,
                "face_enrolled": member.face_enrolled,
                "must_change_password": member.must_change_password,
            }
            for member in team
        ],
        "trainings": trainings_payload,
        "reservations": reservations_payload,
        "today": today.isoformat(),
    }


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
def create_reservations(
    payload: ReservationCreate,
    request: Request,
    leader: User = Depends(require_roles(Role.LIDER)),
    db: Session = Depends(get_db),
) -> dict:
    team = _team(db, leader)
    team_by_id = {member.id: member for member in team}
    if any(employee_id not in team_by_id for employee_id in payload.employee_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione somente integrantes ativos do seu time.",
        )

    training = db.get(Training, payload.training_id)
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
    if training.status != TrainingStatus.AGENDADO.value or training.date < date_type.today():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este treinamento não está mais aberto para reservas.",
        )

    existing_rows = db.scalars(
        select(Reservation).where(
            Reservation.training_id == training.id,
            Reservation.employee_id.in_(payload.employee_ids),
        )
    ).all()
    existing_by_employee = {reservation.employee_id: reservation for reservation in existing_rows}
    already_active = [
        team_by_id[reservation.employee_id].name
        for reservation in existing_rows
        if reservation.status == ReservationStatus.ATIVA.value
    ]
    if already_active:
        names = ", ".join(sorted(already_active))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe reserva ativa para: {names}.",
        )

    active_count = db.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.training_id == training.id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
    ) or 0
    if active_count + len(payload.employee_ids) > training.seats:
        available = max(training.seats - active_count, 0)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vagas insuficientes. Restam {available} vaga(s) nesta turma.",
        )

    now = utcnow()
    for employee_id in payload.employee_ids:
        reservation = existing_by_employee.get(employee_id)
        if reservation:
            reservation.status = ReservationStatus.ATIVA.value
            reservation.created_by_id = leader.id
            reservation.created_at = now
            reservation.cancelled_at = None
        else:
            reservation = Reservation(
                training_id=training.id,
                employee_id=employee_id,
                created_by_id=leader.id,
                status=ReservationStatus.ATIVA.value,
                created_at=now,
            )
            db.add(reservation)
        queue_reservation_confirmed_email(
            db,
            user=team_by_id[employee_id],
            training=training,
            reserved_by=leader,
            base_url=site_url(request),
        )

    log_action(
        db,
        actor_id=leader.id,
        action="reserva_criada",
        entity="training",
        entity_id=training.id,
        details={"employee_ids": payload.employee_ids},
        ip_address=client_ip(request),
    )
    db.commit()
    return {"ok": True, "created": len(payload.employee_ids)}


@router.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    request: Request,
    leader: User = Depends(require_roles(Role.LIDER)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(
        select(Reservation, Training, User)
        .join(Training, Training.id == Reservation.training_id)
        .join(User, User.id == Reservation.employee_id)
        .where(Reservation.id == reservation_id)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada.")
    reservation, training, employee = row
    if employee.leader_id != leader.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada.")
    if reservation.status != ReservationStatus.ATIVA.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta reserva já foi cancelada.",
        )
    if training.status == TrainingStatus.CONCLUIDO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservas de uma turma concluída não podem ser canceladas.",
        )
    attendance_exists = db.scalar(
        select(Attendance.id).where(
            Attendance.training_id == training.id,
            Attendance.employee_id == employee.id,
        )
    )
    if attendance_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A presença já foi registrada nesta turma; a reserva não pode ser cancelada.",
        )

    reservation.status = ReservationStatus.CANCELADA.value
    reservation.cancelled_at = utcnow()
    queue_reservation_cancelled_email(
        db,
        user=employee,
        training=training,
        cancelled_by=leader,
    )
    log_action(
        db,
        actor_id=leader.id,
        action="reserva_cancelada",
        entity="reservation",
        entity_id=reservation.id,
        details={"training_id": training.id, "employee_id": employee.id},
        ip_address=client_ip(request),
    )
    db.commit()
    return {"ok": True}
