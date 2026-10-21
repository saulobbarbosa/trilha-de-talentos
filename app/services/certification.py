from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    Certificate,
    Reservation,
    ReservationStatus,
    Training,
    TrainingStatus,
    User,
    utcnow,
)
from app.security import generate_certificate_code
from app.services.email import queue_certificate_issued_email

COMPLETABLE_STATUSES = {
    TrainingStatus.AGENDADO.value,
    TrainingStatus.EM_ANDAMENTO.value,
}


def _iso_utc(value: datetime | None) -> str | None:
    return f"{value.isoformat()}Z" if value else None


def certificate_payload(certificate: Certificate, employee: User) -> dict:
    return {
        "id": certificate.id,
        "employee_id": employee.id,
        "employee_name": employee.name,
        "code": certificate.verification_code,
        "issued_at": _iso_utc(certificate.issued_at),
    }


def participant_rows(db: Session, training: Training) -> list[tuple[User, Attendance | None, Certificate | None]]:
    rows = db.execute(
        select(User, Attendance, Certificate)
        .join(Reservation, Reservation.employee_id == User.id)
        .outerjoin(
            Attendance,
            and_(
                Attendance.training_id == training.id,
                Attendance.employee_id == User.id,
            ),
        )
        .outerjoin(
            Certificate,
            and_(
                Certificate.training_id == training.id,
                Certificate.employee_id == User.id,
            ),
        )
        .where(
            Reservation.training_id == training.id,
            Reservation.status == ReservationStatus.ATIVA.value,
            User.is_active.is_(True),
        )
        .order_by(User.name)
    ).all()
    return [(employee, attendance, certificate) for employee, attendance, certificate in rows]


def completion_state(
    training: Training,
    rows: list[tuple[User, Attendance | None, Certificate | None]],
) -> dict:
    reserved = len(rows)
    present = sum(1 for _employee, attendance, _certificate in rows if attendance is not None)
    pending = max(reserved - present, 0)
    certificates = sum(1 for _employee, _attendance, certificate in rows if certificate is not None)

    blocked_reason: str | None = None
    if training.status == TrainingStatus.CANCELADO.value:
        blocked_reason = "Uma turma cancelada não pode ser concluída."
    elif training.status == TrainingStatus.CONCLUIDO.value:
        blocked_reason = "Esta turma já foi concluída."
    elif training.status not in COMPLETABLE_STATUSES:
        blocked_reason = "Esta turma não está disponível para encerramento."
    elif reserved == 0:
        blocked_reason = "A turma não possui participantes com reserva ativa."

    warnings: list[str] = []
    if blocked_reason is None:
        if present == 0:
            warnings.append("Nenhuma presença foi registrada; a turma será concluída sem certificados.")
        elif pending:
            verb = "receberá" if pending == 1 else "receberão"
            warnings.append(
                f"{pending} participante{'s' if pending != 1 else ''} "
                f"sem presença não {verb} certificado."
            )
        if training.date > date.today():
            warnings.append("A data da turma ainda não chegou.")

    return {
        "can_complete": blocked_reason is None,
        "blocked_reason": blocked_reason,
        "warnings": warnings,
        "reserved": reserved,
        "present": present,
        "pending": pending,
        "eligible_count": present,
        "certificate_count": certificates,
        "completed_at": _iso_utc(training.completed_at),
    }


def _unique_certificate_code(db: Session) -> str:
    for _ in range(20):
        code = generate_certificate_code()
        exists = db.scalar(select(Certificate.id).where(Certificate.verification_code == code))
        if not exists:
            return code
    raise RuntimeError("Não foi possível gerar um código de certificado único.")


def complete_training(
    db: Session,
    *,
    training: Training,
    rows: list[tuple[User, Attendance | None, Certificate | None]],
    base_url: str,
) -> list[tuple[Certificate, User]]:
    issued: list[tuple[Certificate, User]] = []
    completed_at = utcnow()

    for employee, attendance, certificate in rows:
        if attendance is None or certificate is not None:
            continue
        certificate = Certificate(
            training_id=training.id,
            employee_id=employee.id,
            verification_code=_unique_certificate_code(db),
            issued_at=completed_at,
        )
        db.add(certificate)
        db.flush()
        queue_certificate_issued_email(
            db,
            user=employee,
            training=training,
            certificate=certificate,
            base_url=base_url,
        )
        issued.append((certificate, employee))

    training.status = TrainingStatus.CONCLUIDO.value
    training.completed_at = completed_at
    db.flush()
    return issued
