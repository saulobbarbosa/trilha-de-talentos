from __future__ import annotations

import re
import uuid
from datetime import date, time

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Attendance,
    AttendanceMethod,
    AuditLog,
    Certificate,
    OutboxEmail,
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
)
from app.security import hash_password
from tests.helpers import csrf_token, login


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _create_completion_data(
    *,
    with_attendance: bool = True,
    with_participants: bool = True,
    status: str = TrainingStatus.AGENDADO.value,
) -> dict:
    suffix = _suffix()
    db = SessionLocal()
    try:
        instructor = db.scalar(select(User).where(User.email == "teste.instrutor@lins.local"))
        leader = db.scalar(select(User).where(User.email == "teste.lider@lins.local"))
        rh = db.scalar(select(User).where(User.email == "teste.rh@lins.local"))
        assert instructor and leader and rh

        present_employee = User(
            name=f"Presente M5 {suffix}",
            email=f"m5.presente.{suffix}@lins.local",
            password_hash=hash_password("M5Presente@2026"),
            role=Role.FUNCIONARIO.value,
            leader_id=leader.id,
            must_change_password=False,
            face_enrolled=False,
            is_active=True,
        )
        absent_employee = User(
            name=f"Ausente M5 {suffix}",
            email=f"m5.ausente.{suffix}@lins.local",
            password_hash=hash_password("M5Ausente@2026"),
            role=Role.FUNCIONARIO.value,
            leader_id=leader.id,
            must_change_password=False,
            face_enrolled=False,
            is_active=True,
        )
        db.add_all([present_employee, absent_employee])
        db.flush()

        training = Training(
            title=f"Conclusao M5 {suffix}",
            description="Turma criada para os testes automatizados do Marco 5.",
            instructor_id=instructor.id,
            date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            location="Sala de testes",
            seats=10,
            workload_hours=8,
            status=status,
            created_by_id=rh.id,
        )
        db.add(training)
        db.flush()

        reservations: dict[int, Reservation] = {}
        if with_participants:
            for employee in (present_employee, absent_employee):
                reservation = Reservation(
                    training_id=training.id,
                    employee_id=employee.id,
                    created_by_id=leader.id,
                    status=ReservationStatus.ATIVA.value,
                )
                db.add(reservation)
                reservations[employee.id] = reservation
            db.flush()

        if with_attendance:
            db.add(
                Attendance(
                    training_id=training.id,
                    employee_id=present_employee.id,
                    instructor_id=instructor.id,
                    method=AttendanceMethod.MANUAL.value,
                    justification="Presenca confirmada para o teste de certificacao.",
                )
            )
        db.commit()
        return {
            "training_id": training.id,
            "present_employee_id": present_employee.id,
            "present_email": present_employee.email,
            "present_password": "M5Presente@2026",
            "absent_employee_id": absent_employee.id,
            "absent_email": absent_employee.email,
            "absent_password": "M5Ausente@2026",
            "present_reservation_id": reservations.get(present_employee.id).id
            if present_employee.id in reservations
            else None,
            "absent_reservation_id": reservations.get(absent_employee.id).id
            if absent_employee.id in reservations
            else None,
            "instructor_id": instructor.id,
        }
    finally:
        db.close()


@pytest.fixture
def completion_data():
    return _create_completion_data()


def _login_instructor(client) -> None:
    response = login(client, "teste.instrutor@lins.local", "TesteInstrutor@2026")
    assert response.status_code == 200, response.text


def _complete(client, training_id: int, *, csrf: bool = True):
    headers = {"X-CSRF-Token": csrf_token(client)} if csrf else {}
    return client.post(f"/api/instructor/trainings/{training_id}/complete", headers=headers)


def test_completion_issues_certificate_and_public_verification(client, completion_data):
    training_id = completion_data["training_id"]
    _login_instructor(client)

    detail = client.get(f"/api/instructor/trainings/{training_id}/attendance")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["completion"]["can_complete"] is True
    assert body["completion"]["eligible_count"] == 1
    assert body["completion"]["pending"] == 1
    assert body["completion"]["certificate_count"] == 0
    assert "não receberá" in body["completion"]["warnings"][0]

    missing_csrf = _complete(client, training_id, csrf=False)
    assert missing_csrf.status_code == 403

    completed = _complete(client, training_id)
    assert completed.status_code == 200, completed.text
    completed_body = completed.json()
    assert completed_body["certificates_issued"] == 1
    assert completed_body["training"]["status"] == TrainingStatus.CONCLUIDO.value
    assert completed_body["training"]["certificate_count"] == 1
    assert completed_body["completion"]["can_complete"] is False
    certificate = completed_body["certificates"][0]
    assert certificate["employee_id"] == completion_data["present_employee_id"]
    assert re.fullmatch(r"LINS-[A-Z2-9]{5}-[A-Z2-9]{5}-[A-Z2-9]{5}", certificate["code"])

    db = SessionLocal()
    try:
        certificates = list(
            db.scalars(select(Certificate).where(Certificate.training_id == training_id)).all()
        )
        assert len(certificates) == 1
        assert certificates[0].employee_id == completion_data["present_employee_id"]
        training = db.get(Training, training_id)
        assert training and training.completed_at is not None
        actions = list(db.scalars(select(AuditLog.action)).all())
        assert "treinamento_concluido" in actions
        assert "certificado_emitido" in actions
        outbox = db.scalar(
            select(OutboxEmail).where(
                OutboxEmail.recipient == completion_data["present_email"],
                OutboxEmail.subject == f"Certificado emitido: {training.title}",
            )
        )
        assert outbox is not None
        assert certificate["code"] in outbox.body
    finally:
        db.close()

    verification = client.get(f"/api/certificates/verify/{certificate['code']}")
    assert verification.status_code == 200, verification.text
    verified = verification.json()
    assert verified["valid"] is True
    assert verified["holder_name"].startswith("Presente M5")
    assert verified["code"] == certificate["code"]

    refreshed = client.get(f"/api/instructor/trainings/{training_id}/attendance").json()
    assert refreshed["completion"]["certificate_count"] == 1
    assert refreshed["completion"]["can_complete"] is False
    present_row = next(
        item
        for item in refreshed["participants"]
        if item["employee_id"] == completion_data["present_employee_id"]
    )
    assert present_row["certificate"]["code"] == certificate["code"]

    duplicate = _complete(client, training_id)
    assert duplicate.status_code == 409
    assert "já foi concluída" in duplicate.json()["detail"]

    remove_attendance = client.delete(
        f"/api/instructor/trainings/{training_id}/attendance/{present_row['attendance']['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert remove_attendance.status_code == 409

    present_login = login(
        client, completion_data["present_email"], completion_data["present_password"]
    )
    assert present_login.status_code == 200
    present_home = client.get("/api/home").json()
    assert len(present_home["certificates"]) == 1
    assert present_home["certificates"][0]["code"] == certificate["code"]

    absent_login = login(client, completion_data["absent_email"], completion_data["absent_password"])
    assert absent_login.status_code == 200
    absent_home = client.get("/api/home").json()
    assert absent_home["certificates"] == []

    leader_login = login(client, "teste.lider@lins.local", "TesteLider@2026")
    assert leader_login.status_code == 200
    cancel = client.post(
        f"/api/leader/reservations/{completion_data['absent_reservation_id']}/cancel",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert cancel.status_code == 409
    assert "concluída" in cancel.json()["detail"]


def test_completion_guards_and_empty_call(client, completion_data):
    training_id = completion_data["training_id"]

    assert _complete(client, training_id).status_code == 401

    employee_login = login(
        client, completion_data["present_email"], completion_data["present_password"]
    )
    assert employee_login.status_code == 200
    assert _complete(client, training_id).status_code == 403

    other = _create_completion_data()
    _login_instructor(client)
    assert _complete(client, other["training_id"]).status_code == 200

    empty = _create_completion_data(with_participants=False, with_attendance=False)
    empty_response = _complete(client, empty["training_id"])
    assert empty_response.status_code == 409
    assert "reserva ativa" in empty_response.json()["detail"]

    canceled = _create_completion_data(status=TrainingStatus.CANCELADO.value)
    canceled_response = _complete(client, canceled["training_id"])
    assert canceled_response.status_code == 409
    assert "cancelada" in canceled_response.json()["detail"]


def test_completion_without_attendance_issues_no_certificates(client):
    data = _create_completion_data(with_attendance=False)
    _login_instructor(client)

    preview = client.get(f"/api/instructor/trainings/{data['training_id']}/attendance")
    assert preview.status_code == 200, preview.text
    assert preview.json()["completion"]["can_complete"] is True
    assert "Nenhuma presença" in preview.json()["completion"]["warnings"][0]

    response = _complete(client, data["training_id"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["certificates_issued"] == 0
    assert body["certificates"] == []
    assert body["completion"]["certificate_count"] == 0
    assert body["completion"]["pending"] == 2

    db = SessionLocal()
    try:
        assert (
            db.scalar(select(Certificate.id).where(Certificate.training_id == data["training_id"]))
            is None
        )
    finally:
        db.close()
