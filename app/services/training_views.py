from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Attendance, Certificate, Reservation, ReservationStatus, Training, TrainingStatus


def active_reservation_counts(db: Session, training_ids: list[int]) -> dict[int, int]:
    if not training_ids:
        return {}
    rows = db.execute(
        select(Reservation.training_id, func.count(Reservation.id))
        .where(
            Reservation.training_id.in_(training_ids),
            Reservation.status == ReservationStatus.ATIVA.value,
        )
        .group_by(Reservation.training_id)
    ).all()
    return {training_id: count for training_id, count in rows}


def training_payload(db: Session, training: Training, reserved: int | None = None) -> dict:
    if reserved is None:
        reserved = db.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.training_id == training.id,
                Reservation.status == ReservationStatus.ATIVA.value,
            )
        ) or 0

    reservation_count = db.scalar(
        select(func.count(Reservation.id)).where(Reservation.training_id == training.id)
    ) or 0
    attendance_count = db.scalar(
        select(func.count(Attendance.id)).where(Attendance.training_id == training.id)
    ) or 0
    certificate_count = db.scalar(
        select(func.count(Certificate.id)).where(Certificate.training_id == training.id)
    ) or 0
    scheduled = training.status == TrainingStatus.AGENDADO.value
    can_delete = reservation_count == 0 and attendance_count == 0 and certificate_count == 0

    return {
        "id": training.id,
        "title": training.title,
        "description": training.description,
        "instructor_id": training.instructor_id,
        "instructor": training.instructor.name if training.instructor else "",
        "date": training.date.isoformat(),
        "start_time": training.start_time.strftime("%H:%M"),
        "end_time": training.end_time.strftime("%H:%M"),
        "location": training.location,
        "seats": training.seats,
        "reserved": reserved,
        "available": max(training.seats - reserved, 0),
        "workload_hours": training.workload_hours,
        "status": training.status,
        "reservation_count": reservation_count,
        "attendance_count": attendance_count,
        "certificate_count": certificate_count,
        "can_edit": scheduled,
        "can_cancel": scheduled,
        "can_delete": can_delete,
    }
