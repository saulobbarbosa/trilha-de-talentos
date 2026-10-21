from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_roles
from app.models import (
    Attendance,
    AttendanceMethod,
    FaceEmbedding,
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
)
from app.security import client_ip, require_csrf
from app.services.audit import log_action
from app.services.certification import (
    certificate_payload,
    complete_training,
    completion_state,
    participant_rows,
)
from app.services.email import site_url
from app.services.face import (
    FaceServiceError,
    cosine_similarity,
    get_face_service,
    vector_from_bytes,
)

router = APIRouter(prefix="/api/instructor", tags=["instrutor"])
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
GENERIC_CONTENT_TYPES = {"", "application/octet-stream"}
RECORDABLE_STATUSES = {TrainingStatus.AGENDADO.value, TrainingStatus.EM_ANDAMENTO.value}


class ManualAttendanceRequest(BaseModel):
    employee_id: int
    justification: str = Field(min_length=5, max_length=300)

    @field_validator("justification")
    @classmethod
    def _trim_justification(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 5:
            raise ValueError("Informe o motivo do registro manual.")
        return value


def _iso_utc(value: datetime | None) -> str | None:
    return f"{value.isoformat()}Z" if value else None


def _owned_training(db: Session, instructor: User, training_id: int) -> Training:
    training = db.get(Training, training_id)
    if not training or training.instructor_id != instructor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treinamento não encontrado entre as suas turmas.",
        )
    return training


def _blocked_reason(training: Training, participants_count: int) -> str | None:
    if training.status == TrainingStatus.CANCELADO.value:
        return "Este treinamento foi cancelado."
    if training.status == TrainingStatus.CONCLUIDO.value:
        return "A chamada desta turma já foi encerrada."
    if training.status not in RECORDABLE_STATUSES:
        return "Esta turma não está disponível para chamada."
    if participants_count == 0:
        return "Ainda não há participantes com reserva ativa nesta turma."
    return None


def _attendance_payload(attendance: Attendance) -> dict:
    return {
        "id": attendance.id,
        "employee_id": attendance.employee_id,
        "method": attendance.method,
        "score": attendance.score,
        "justification": attendance.justification,
        "recorded_at": _iso_utc(attendance.recorded_at),
        "instructor": attendance.instructor.name if attendance.instructor else "",
    }


def _call_payload(db: Session, training: Training) -> dict:
    participant_records = participant_rows(db, training)
    attendances = [
        attendance for _employee, attendance, _certificate in participant_records if attendance
    ]

    rows = []
    for employee, attendance, certificate in participant_records:
        rows.append(
            {
                "employee_id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "face_enrolled": employee.face_enrolled,
                "status": "presente" if attendance else "pendente",
                "attendance": _attendance_payload(attendance) if attendance else None,
                "certificate": certificate_payload(certificate, employee) if certificate else None,
            }
        )

    face_count = sum(1 for item in attendances if item.method == AttendanceMethod.FACE.value)
    manual_count = sum(1 for item in attendances if item.method == AttendanceMethod.MANUAL.value)
    blocked_reason = _blocked_reason(training, len(participant_records))
    completion = completion_state(training, participant_records)

    return {
        "training": {
            "id": training.id,
            "title": training.title,
            "description": training.description,
            "date": training.date.isoformat(),
            "start_time": training.start_time.strftime("%H:%M"),
            "end_time": training.end_time.strftime("%H:%M"),
            "location": training.location,
            "status": training.status,
            "instructor": training.instructor.name if training.instructor else "",
            "reserved": len(participant_records),
            "certificate_count": completion["certificate_count"],
            "completed_at": completion["completed_at"],
        },
        "participants": rows,
        "summary": {
            "reserved": len(participant_records),
            "present": len(attendances),
            "pending": max(len(participant_records) - len(attendances), 0),
            "face": face_count,
            "manual": manual_count,
        },
        "recognition": {
            "enrolled_candidates": sum(
                1 for employee, _attendance, _certificate in participant_records if employee.face_enrolled
            ),
            "threshold": settings.face_threshold,
            "margin": settings.face_margin,
        },
        "completion": completion,
        "can_record": blocked_reason is None,
        "blocked_reason": blocked_reason,
        "is_today": training.date == date.today(),
    }


def _employee_payload(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "face_enrolled": user.face_enrolled,
    }


@router.get("/trainings/{training_id}/attendance")
def attendance_detail(
    training_id: int,
    instructor: User = Depends(require_roles(Role.INSTRUTOR)),
    db: Session = Depends(get_db),
) -> dict:
    training = _owned_training(db, instructor, training_id)
    return _call_payload(db, training)


@router.post("/trainings/{training_id}/complete")
def complete_training_call(
    training_id: int,
    request: Request,
    instructor: User = Depends(require_roles(Role.INSTRUTOR)),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    training = _owned_training(db, instructor, training_id)
    records = participant_rows(db, training)
    completion = completion_state(training, records)
    if not completion["can_complete"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=completion["blocked_reason"] or "Esta turma não pode ser concluída.",
        )

    issued = complete_training(
        db,
        training=training,
        rows=records,
        base_url=site_url(request),
    )
    for certificate, employee in issued:
        log_action(
            db,
            actor_id=instructor.id,
            action="certificado_emitido",
            entity="certificate",
            entity_id=certificate.id,
            details={
                "training_id": training.id,
                "employee_id": employee.id,
                "code": certificate.verification_code,
            },
            ip_address=client_ip(request),
        )
    log_action(
        db,
        actor_id=instructor.id,
        action="treinamento_concluido",
        entity="training",
        entity_id=training.id,
        details={
            "certificates_issued": len(issued),
            "pending": completion["pending"],
        },
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(training)

    payload = _call_payload(db, training)
    return {
        "ok": True,
        "certificates_issued": len(issued),
        "certificates": [
            certificate_payload(certificate, employee) for certificate, employee in issued
        ],
        "training": payload["training"],
        "completion": payload["completion"],
    }


@router.post("/trainings/{training_id}/attendance/face", status_code=status.HTTP_201_CREATED)
def record_face_attendance(
    training_id: int,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    instructor: User = Depends(require_roles(Role.INSTRUTOR)),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    training = _owned_training(db, instructor, training_id)
    participants_count = len(
        db.scalars(
            select(User.id)
            .join(Reservation, Reservation.employee_id == User.id)
            .where(
                Reservation.training_id == training.id,
                Reservation.status == ReservationStatus.ATIVA.value,
                User.is_active.is_(True),
            )
        ).all()
    )
    blocked_reason = _blocked_reason(training, participants_count)
    if blocked_reason:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=blocked_reason)

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES and content_type not in GENERIC_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie uma imagem JPG, PNG ou WebP.",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    raw = file.file.read(max_bytes + 1)
    file.file.close()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A imagem enviada está vazia.")
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"A imagem deve ter no máximo {settings.max_upload_mb} MB.",
        )

    service = get_face_service()
    try:
        sample = service.analyze(raw)
    except FaceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    rows = db.execute(
        select(Reservation.employee_id, User.name, User.face_enrolled, FaceEmbedding.vector)
        .join(User, User.id == Reservation.employee_id)
        .join(FaceEmbedding, FaceEmbedding.user_id == Reservation.employee_id)
        .where(
            Reservation.training_id == training.id,
            Reservation.status == ReservationStatus.ATIVA.value,
            User.is_active.is_(True),
            User.face_enrolled.is_(True),
        )
    ).all()

    scores: dict[int, float] = {}
    names: dict[int, str] = {}
    for employee_id, name, _enrolled, stored_vector in rows:
        try:
            vector = vector_from_bytes(stored_vector)
        except ValueError:
            continue
        score = cosine_similarity(sample.embedding, vector)
        scores[employee_id] = max(scores.get(employee_id, -1.0), score)
        names[employee_id] = name

    if not scores:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nenhum participante com cadastro facial disponível. Use o registro manual.",
        )

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_employee_id, best_score = ranked[0]
    if best_score < settings.face_threshold:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rosto não reconhecido entre os participantes. Tente outra captura ou use o registro manual.",
        )

    if len(ranked) > 1 and best_score - ranked[1][1] < settings.face_margin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O reconhecimento ficou ambíguo entre participantes. Use o registro manual para confirmar.",
        )

    employee = db.get(User, best_employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participante não encontrado.")

    existing = db.scalar(
        select(Attendance).where(
            Attendance.training_id == training.id,
            Attendance.employee_id == employee.id,
        )
    )
    if existing:
        response.status_code = status.HTTP_200_OK
        return {
            "ok": True,
            "already_recorded": True,
            "employee": _employee_payload(employee),
            "attendance": _attendance_payload(existing),
            "summary": _call_payload(db, training)["summary"],
        }

    attendance = Attendance(
        training_id=training.id,
        employee_id=employee.id,
        instructor_id=instructor.id,
        method=AttendanceMethod.FACE.value,
        score=round(float(best_score), 4),
    )
    db.add(attendance)
    db.flush()
    log_action(
        db,
        actor_id=instructor.id,
        action="presenca_registrada_facial",
        entity="attendance",
        entity_id=attendance.id,
        details={
            "training_id": training.id,
            "employee_id": employee.id,
            "score": attendance.score,
            "threshold": settings.face_threshold,
            "margin": settings.face_margin,
            "model_name": sample.model_name,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return {
        "ok": True,
        "already_recorded": False,
        "employee": _employee_payload(employee),
        "attendance": _attendance_payload(attendance),
        "summary": _call_payload(db, training)["summary"],
    }


@router.post("/trainings/{training_id}/attendance/manual", status_code=status.HTTP_201_CREATED)
def record_manual_attendance(
    training_id: int,
    payload: ManualAttendanceRequest,
    request: Request,
    instructor: User = Depends(require_roles(Role.INSTRUTOR)),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    training = _owned_training(db, instructor, training_id)

    reservation = db.scalar(
        select(Reservation).where(
            Reservation.training_id == training.id,
            Reservation.employee_id == payload.employee_id,
            Reservation.status == ReservationStatus.ATIVA.value,
        )
    )
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este participante não possui reserva ativa nesta turma.",
        )

    participants_count = len(
        db.scalars(
            select(Reservation.id).where(
                Reservation.training_id == training.id,
                Reservation.status == ReservationStatus.ATIVA.value,
            )
        ).all()
    )
    blocked_reason = _blocked_reason(training, participants_count)
    if blocked_reason:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=blocked_reason)

    employee = db.get(User, payload.employee_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participante não encontrado.")

    existing = db.scalar(
        select(Attendance).where(
            Attendance.training_id == training.id,
            Attendance.employee_id == employee.id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A presença de {employee.name} já foi registrada.",
        )

    attendance = Attendance(
        training_id=training.id,
        employee_id=employee.id,
        instructor_id=instructor.id,
        method=AttendanceMethod.MANUAL.value,
        justification=payload.justification,
    )
    db.add(attendance)
    db.flush()
    log_action(
        db,
        actor_id=instructor.id,
        action="presenca_registrada_manual",
        entity="attendance",
        entity_id=attendance.id,
        details={
            "training_id": training.id,
            "employee_id": employee.id,
            "justification": payload.justification,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return {
        "ok": True,
        "employee": _employee_payload(employee),
        "attendance": _attendance_payload(attendance),
        "summary": _call_payload(db, training)["summary"],
    }


@router.delete("/trainings/{training_id}/attendance/{attendance_id}")
def remove_attendance(
    training_id: int,
    attendance_id: int,
    request: Request,
    instructor: User = Depends(require_roles(Role.INSTRUTOR)),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    training = _owned_training(db, instructor, training_id)
    attendance = db.get(Attendance, attendance_id)
    if not attendance or attendance.training_id != training.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presença não encontrada.")
    if training.status == TrainingStatus.CONCLUIDO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Presenças de uma turma concluída não podem ser removidas.",
        )

    employee_id = attendance.employee_id
    method = attendance.method
    db.delete(attendance)
    log_action(
        db,
        actor_id=instructor.id,
        action="presenca_removida",
        entity="attendance",
        entity_id=attendance_id,
        details={
            "training_id": training.id,
            "employee_id": employee_id,
            "method": method,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return {
        "ok": True,
        "employee_id": employee_id,
        "summary": _call_payload(db, training)["summary"],
    }
