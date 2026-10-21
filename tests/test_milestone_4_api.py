from __future__ import annotations

import uuid
from datetime import date, time

import numpy as np
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Attendance,
    AttendanceMethod,
    AuditLog,
    FaceEmbedding,
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
)
from app.security import hash_password
from app.services.face import FaceSample, FaceServiceUnavailable
from tests.helpers import csrf_token, login


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _vector(x: float, y: float) -> np.ndarray:
    vector = np.zeros(512, dtype=np.float32)
    vector[0] = x
    vector[1] = y
    return vector / float(np.linalg.norm(vector))


def _create_call_data() -> dict:
    suffix = _suffix()
    db = SessionLocal()
    try:
        instructor = db.scalar(select(User).where(User.email == "teste.instrutor@lins.local"))
        leader = db.scalar(select(User).where(User.email == "teste.lider@lins.local"))
        rh = db.scalar(select(User).where(User.email == "teste.rh@lins.local"))
        assert instructor and leader and rh

        face_employee = User(
            name=f"Participante Facial {suffix}",
            email=f"m4.face.{suffix}@lins.local",
            password_hash=hash_password("M4Face@2026"),
            role=Role.FUNCIONARIO.value,
            leader_id=leader.id,
            must_change_password=False,
            face_enrolled=True,
            is_active=True,
        )
        manual_employee = User(
            name=f"Participante Manual {suffix}",
            email=f"m4.manual.{suffix}@lins.local",
            password_hash=hash_password("M4Manual@2026"),
            role=Role.FUNCIONARIO.value,
            leader_id=leader.id,
            must_change_password=False,
            face_enrolled=False,
            is_active=True,
        )
        outsider = User(
            name=f"Sem Reserva {suffix}",
            email=f"m4.outsider.{suffix}@lins.local",
            password_hash=hash_password("M4Outsider@2026"),
            role=Role.FUNCIONARIO.value,
            leader_id=leader.id,
            must_change_password=False,
            face_enrolled=True,
            is_active=True,
        )
        db.add_all([face_employee, manual_employee, outsider])
        db.flush()

        training = Training(
            title=f"Chamada M4 {suffix}",
            description="Turma criada para os testes automatizados do Marco 4.",
            instructor_id=instructor.id,
            date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            location="Sala de testes",
            seats=10,
            workload_hours=8,
            status=TrainingStatus.AGENDADO.value,
            created_by_id=rh.id,
        )
        db.add(training)
        db.flush()

        db.add_all(
            [
                Reservation(
                    training_id=training.id,
                    employee_id=face_employee.id,
                    created_by_id=leader.id,
                    status=ReservationStatus.ATIVA.value,
                ),
                Reservation(
                    training_id=training.id,
                    employee_id=manual_employee.id,
                    created_by_id=leader.id,
                    status=ReservationStatus.ATIVA.value,
                ),
            ]
        )
        for employee, vector in [
            (face_employee, _vector(1.0, 0.0)),
            (outsider, _vector(0.0, 1.0)),
        ]:
            for _ in range(3):
                db.add(FaceEmbedding(user_id=employee.id, vector=vector.tobytes()))
        db.commit()
        return {
            "training_id": training.id,
            "face_employee_id": face_employee.id,
            "face_employee_name": face_employee.name,
            "manual_employee_id": manual_employee.id,
            "manual_employee_name": manual_employee.name,
            "outsider_id": outsider.id,
            "face_email": face_employee.email,
            "face_password": "M4Face@2026",
            "instructor_id": instructor.id,
        }
    finally:
        db.close()


@pytest.fixture
def call_data():
    return _create_call_data()


@pytest.fixture
def fake_face(monkeypatch):
    state: dict = {"vector": _vector(1.0, 0.0), "error": None}

    class FakeFaceService:
        loaded = True

        def analyze(self, _data: bytes) -> FaceSample:
            if state["error"]:
                raise state["error"]
            return FaceSample(
                embedding=state["vector"],
                detection_score=0.95,
                quality=0.95,
                bbox=(100, 100, 360, 460),
            )

    service = FakeFaceService()
    monkeypatch.setattr("app.routers.instructor.get_face_service", lambda: service)
    return state


def _login_instructor(client):
    response = login(client, "teste.instrutor@lins.local", "TesteInstrutor@2026")
    assert response.status_code == 200, response.text


def _upload_face(client, training_id: int, content: bytes = b"known", *, csrf: bool = True):
    headers = {"X-CSRF-Token": csrf_token(client)} if csrf else {}
    return client.post(
        f"/api/instructor/trainings/{training_id}/attendance/face",
        headers=headers,
        files={"file": ("presenca.jpg", content, "image/jpeg")},
    )


def test_instructor_call_access_and_detail(client, call_data):
    training_id = call_data["training_id"]
    assert client.get(f"/api/instructor/trainings/{training_id}/attendance").status_code == 401

    response = login(client, call_data["face_email"], call_data["face_password"])
    assert response.status_code == 200
    forbidden = client.get(f"/api/instructor/trainings/{training_id}/attendance")
    assert forbidden.status_code == 403

    _login_instructor(client)
    detail = client.get(f"/api/instructor/trainings/{training_id}/attendance")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["training"]["id"] == training_id
    assert body["summary"] == {
        "reserved": 2,
        "present": 0,
        "pending": 2,
        "face": 0,
        "manual": 0,
    }
    assert body["recognition"]["enrolled_candidates"] == 1
    assert body["can_record"] is True
    assert body["is_today"] is True
    assert len(body["participants"]) == 2
    assert not client.get("/api/instructor/trainings/999999/attendance").is_success


def test_face_attendance_success_duplicate_and_audit(client, call_data, fake_face):
    _login_instructor(client)
    training_id = call_data["training_id"]

    missing_csrf = _upload_face(client, training_id, csrf=False)
    assert missing_csrf.status_code == 403

    response = _upload_face(client, training_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["already_recorded"] is False
    assert body["employee"]["id"] == call_data["face_employee_id"]
    assert body["attendance"]["method"] == AttendanceMethod.FACE.value
    assert body["attendance"]["score"] > 0.99
    assert body["summary"]["present"] == 1
    assert body["summary"]["face"] == 1

    duplicate = _upload_face(client, training_id)
    assert duplicate.status_code == 200
    assert duplicate.json()["already_recorded"] is True
    assert duplicate.json()["summary"]["present"] == 1

    removed = client.delete(
        f"/api/instructor/trainings/{training_id}/attendance/{body['attendance']['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["summary"]["present"] == 0

    db = SessionLocal()
    try:
        attendance = db.scalar(select(Attendance).where(Attendance.training_id == training_id))
        assert attendance is None
        actions = db.scalars(select(AuditLog.action)).all()
        assert "presenca_registrada_facial" in actions
        assert "presenca_removida" in actions
    finally:
        db.close()


def test_face_attendance_unknown_and_manual_fallback(client, call_data, fake_face):
    _login_instructor(client)
    training_id = call_data["training_id"]

    fake_face["vector"] = _vector(0.0, 1.0)
    unknown = _upload_face(client, training_id)
    assert unknown.status_code == 422
    assert "não reconhecido" in unknown.json()["detail"]

    short = client.post(
        f"/api/instructor/trainings/{training_id}/attendance/manual",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"employee_id": call_data["manual_employee_id"], "justification": "abc"},
    )
    assert short.status_code == 422

    manual = client.post(
        f"/api/instructor/trainings/{training_id}/attendance/manual",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "employee_id": call_data["manual_employee_id"],
            "justification": "Aluno sem cadastro facial; identidade confirmada pelo instrutor.",
        },
    )
    assert manual.status_code == 201, manual.text
    assert manual.json()["attendance"]["method"] == AttendanceMethod.MANUAL.value
    assert manual.json()["attendance"]["justification"].startswith("Aluno sem cadastro")
    assert manual.json()["summary"]["manual"] == 1

    duplicate = client.post(
        f"/api/instructor/trainings/{training_id}/attendance/manual",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "employee_id": call_data["manual_employee_id"],
            "justification": "Tentativa duplicada de presença.",
        },
    )
    assert duplicate.status_code == 409

    not_reserved = client.post(
        f"/api/instructor/trainings/{training_id}/attendance/manual",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "employee_id": call_data["outsider_id"],
            "justification": "Pessoa sem reserva ativa nesta turma.",
        },
    )
    assert not_reserved.status_code == 404


def test_face_attendance_ambiguous_and_unavailable(client, call_data, fake_face):
    _login_instructor(client)
    training_id = call_data["training_id"]

    db = SessionLocal()
    try:
        manual_employee = db.get(User, call_data["manual_employee_id"])
        assert manual_employee
        manual_employee.face_enrolled = True
        second_vector = _vector(0.99, 0.141067)
        for _ in range(3):
            db.add(FaceEmbedding(user_id=manual_employee.id, vector=second_vector.tobytes()))
        db.commit()
    finally:
        db.close()

    ambiguous = _upload_face(client, training_id)
    assert ambiguous.status_code == 409
    assert "ambíguo" in ambiguous.json()["detail"]

    fake_face["error"] = FaceServiceUnavailable("Modelo facial indisponível.")
    unavailable = _upload_face(client, training_id)
    assert unavailable.status_code == 503
    assert "indisponível" in unavailable.json()["detail"]

    db = SessionLocal()
    try:
        training = db.get(Training, training_id)
        assert training
        training.status = TrainingStatus.CANCELADO.value
        db.commit()
    finally:
        db.close()

    canceled = _upload_face(client, training_id)
    assert canceled.status_code == 409
    assert "cancelado" in canceled.json()["detail"]
