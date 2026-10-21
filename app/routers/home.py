from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_onboarded_user
from app.models import (
    Attendance,
    Certificate,
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
)

router = APIRouter(prefix="/api/home", tags=["inicio"])


def _training_summary(training: Training, reserved: int) -> dict:
    return {
        "id": training.id,
        "title": training.title,
        "date": training.date.isoformat(),
        "start_time": training.start_time.strftime("%H:%M"),
        "end_time": training.end_time.strftime("%H:%M"),
        "location": training.location,
        "status": training.status,
        "instructor": training.instructor.name if training.instructor else "",
        "seats": training.seats,
        "reserved": reserved,
        "available": max(training.seats - reserved, 0),
        "workload_hours": training.workload_hours,
    }


def _active_reservation_counts(db: Session, training_ids: list[int]) -> dict[int, int]:
    if not training_ids:
        return {}
    rows = db.execute(
        select(Reservation.training_id, func.count(Reservation.id))
        .where(Reservation.training_id.in_(training_ids), Reservation.status == ReservationStatus.ATIVA.value)
        .group_by(Reservation.training_id)
    ).all()
    return {training_id: count for training_id, count in rows}


@router.get("")
def home(user: User = Depends(get_onboarded_user), db: Session = Depends(get_db)) -> dict:
    today = date.today()
    if user.role == Role.RH.value:
        return _rh_home(db, user, today)
    if user.role == Role.LIDER.value:
        return _leader_home(db, user, today)
    if user.role == Role.INSTRUTOR.value:
        return _instructor_home(db, user, today)
    return _employee_home(db, user, today)


def _rh_home(db: Session, user: User, today: date) -> dict:
    active_statuses = [TrainingStatus.AGENDADO.value, TrainingStatus.EM_ANDAMENTO.value]
    active_trainings = db.scalar(
        select(func.count(Training.id)).where(Training.status.in_(active_statuses))
    ) or 0
    seats = db.scalar(select(func.coalesce(func.sum(Training.seats), 0)).where(Training.status.in_(active_statuses))) or 0
    active_reservations = db.scalar(
        select(func.count(Reservation.id)).where(Reservation.status == ReservationStatus.ATIVA.value)
    ) or 0
    certificates = db.scalar(select(func.count(Certificate.id))) or 0
    users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0

    trainings = db.scalars(
        select(Training).order_by(Training.date.desc(), Training.start_time.desc()).limit(8)
    ).all()
    reserved = _active_reservation_counts(db, [t.id for t in trainings])

    return {
        "role": user.role,
        "stats": [
            {"label": "Treinamentos ativos", "value": str(active_trainings)},
            {"label": "Vagas ofertadas", "value": str(seats)},
            {"label": "Reservas ativas", "value": str(active_reservations)},
            {"label": "Certificados", "value": str(certificates)},
        ],
        "trainings": [_training_summary(t, reserved.get(t.id, 0)) for t in trainings],
        "people_count": users,
        "today": today.isoformat(),
    }


def _leader_home(db: Session, user: User, today: date) -> dict:
    team = db.scalars(select(User).where(User.leader_id == user.id, User.is_active.is_(True)).order_by(User.name)).all()
    team_ids = [member.id for member in team]

    reservations_count = 0
    if team_ids:
        reservations_count = db.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.employee_id.in_(team_ids), Reservation.status == ReservationStatus.ATIVA.value
            )
        ) or 0

    trainings = db.scalars(
        select(Training)
        .where(
            Training.status == TrainingStatus.AGENDADO.value,
            Training.date >= today,
        )
        .order_by(Training.date, Training.start_time)
        .limit(8)
    ).all()
    reserved = _active_reservation_counts(db, [t.id for t in trainings])

    return {
        "role": user.role,
        "stats": [
            {"label": "Pessoas no time", "value": str(len(team))},
            {"label": "Reservas ativas", "value": str(reservations_count)},
            {"label": "Turmas abertas", "value": str(len(trainings))},
        ],
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
        "trainings": [
            _training_summary(t, reserved.get(t.id, 0)) for t in trainings if reserved.get(t.id, 0) < t.seats
        ],
        "today": today.isoformat(),
    }


def _instructor_home(db: Session, user: User, today: date) -> dict:
    trainings = db.scalars(
        select(Training)
        .where(Training.instructor_id == user.id)
        .order_by(Training.date.desc(), Training.start_time.desc())
        .limit(12)
    ).all()
    reserved = _active_reservation_counts(db, [t.id for t in trainings])
    attendance_counts: dict[int, int] = {}
    certificate_counts: dict[int, int] = {}
    if trainings:
        rows = db.execute(
            select(Attendance.training_id, func.count(Attendance.id))
            .where(Attendance.training_id.in_([t.id for t in trainings]))
            .group_by(Attendance.training_id)
        ).all()
        attendance_counts = {training_id: count for training_id, count in rows}
        certificate_rows = db.execute(
            select(Certificate.training_id, func.count(Certificate.id))
            .where(Certificate.training_id.in_([t.id for t in trainings]))
            .group_by(Certificate.training_id)
        ).all()
        certificate_counts = {training_id: count for training_id, count in certificate_rows}

    payload = []
    for training in trainings:
        item = _training_summary(training, reserved.get(training.id, 0))
        item["attendance_count"] = attendance_counts.get(training.id, 0)
        item["certificate_count"] = certificate_counts.get(training.id, 0)
        payload.append(item)

    upcoming = [t for t in payload if t["status"] in (TrainingStatus.AGENDADO.value, TrainingStatus.EM_ANDAMENTO.value)]

    return {
        "role": user.role,
        "stats": [
            {"label": "Turmas atribuídas", "value": str(len(trainings))},
            {"label": "Turmas ativas", "value": str(len(upcoming))},
            {"label": "Presenças registradas", "value": str(sum(attendance_counts.values()))},
        ],
        "trainings": payload,
        "today": today.isoformat(),
    }


def _employee_home(db: Session, user: User, today: date) -> dict:
    reservations = db.execute(
        select(Reservation, Training)
        .join(Training, Training.id == Reservation.training_id)
        .where(
            Reservation.employee_id == user.id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
        .order_by(Training.date, Training.start_time)
    ).all()

    certificates = db.execute(
        select(Certificate, Training)
        .join(Training, Training.id == Certificate.training_id)
        .where(Certificate.employee_id == user.id)
        .order_by(Certificate.issued_at.desc())
    ).all()

    upcoming = [training for _, training in reservations if training.date >= today]

    return {
        "role": user.role,
        "stats": [
            {"label": "Certificados", "value": str(len(certificates))},
            {"label": "Próximos treinamentos", "value": str(len(upcoming))},
            {
                "label": "Horas certificadas",
                "value": f"{sum(t.workload_hours for _, t in certificates):g}h",
            },
        ],
        "reservations": [
            {
                "id": reservation.id,
                "training_id": training.id,
                "title": training.title,
                "date": training.date.isoformat(),
                "start_time": training.start_time.strftime("%H:%M"),
                "location": training.location,
                "status": training.status,
                "instructor": training.instructor.name if training.instructor else "",
            }
            for reservation, training in reservations
        ],
        "certificates": [
            {
                "id": certificate.id,
                "title": training.title,
                "code": certificate.verification_code,
                "issued_at": certificate.issued_at.isoformat(),
                "date": training.date.isoformat(),
                "workload_hours": training.workload_hours,
            }
            for certificate, training in certificates
        ],
        "today": today.isoformat(),
    }
