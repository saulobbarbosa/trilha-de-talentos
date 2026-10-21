from __future__ import annotations

import uuid

import numpy as np
import pytest
from sqlalchemy import select

from app.services.face import FaceQualityError, FaceSample, FaceServiceUnavailable
from tests.helpers import csrf_token, login


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _login_rh(client):
    response = login(client, "teste.rh@lins.local", "TesteRh@2026")
    assert response.status_code == 200
    return response


def _create_employee(client) -> dict[str, str]:
    _login_rh(client)
    options = client.get("/api/rh/options").json()
    leader_id = options["leaders"][0]["id"]
    suffix = _suffix()
    email = f"m3.funcionario.{suffix}@lins.local"
    response = client.post(
        "/api/rh/people",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "name": f"Funcionário M3 {suffix}",
            "email": email,
            "role": "funcionario",
            "leader_id": leader_id,
        },
    )
    assert response.status_code == 201, response.text
    temporary_password = response.json()["temporary_password"]

    login_response = login(client, email, temporary_password)
    assert login_response.status_code == 200
    new_password = f"FaceTeste@{suffix}Aa1"
    changed = client.post(
        "/api/auth/change-password",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"current_password": temporary_password, "new_password": new_password},
    )
    assert changed.status_code == 200, changed.text
    return {"email": email, "password": new_password, "id": str(response.json()["person"]["id"])}


def _accept_consent(client, version: str = "1.0") -> dict:
    response = client.post(
        "/api/face/consent",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"term_version": version, "accepted": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["status"]


def _upload_sample(client, content: bytes = b"fake-face-image", *, content_type: str = "image/jpeg"):
    return client.post(
        "/api/face/enrollment/samples",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={"file": ("captura.jpg", content, content_type)},
    )


class FakeFaceService:
    loaded = True

    def analyze(self, data: bytes) -> FaceSample:
        if data == b"different-person":
            embedding = np.zeros(512, dtype=np.float32)
            embedding[1] = 1.0
        else:
            embedding = np.zeros(512, dtype=np.float32)
            embedding[0] = 1.0
        return FaceSample(
            embedding=embedding,
            detection_score=0.94,
            quality=0.94,
            bbox=(100, 100, 360, 460),
        )


@pytest.fixture
def fake_face_service(monkeypatch):
    service = FakeFaceService()
    monkeypatch.setattr("app.routers.face.get_face_service", lambda: service)
    return service


def test_face_term_consent_status_and_audit(client, fake_face_service):
    assert client.get("/api/face/term").status_code == 401
    assert client.get("/api/face/status").status_code == 401

    _create_employee(client)
    term = client.get("/api/face/term")
    assert term.status_code == 200
    payload = term.json()
    assert payload["version"] == "1.0"
    assert len(payload["sections"]) >= 6
    assert "LGPD" in payload["sections"][3]["body"]

    status = client.get("/api/face/status").json()
    assert status["term"]["accepted"] is False
    assert status["enrollment"]["samples"] == 0
    assert status["enrollment"]["required"] == 3
    assert status["enrollment"]["complete"] is False
    assert status["enrollment"]["can_capture"] is False

    missing_csrf = client.post(
        "/api/face/consent",
        json={"term_version": "1.0", "accepted": True},
    )
    assert missing_csrf.status_code == 403

    wrong_version = client.post(
        "/api/face/consent",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"term_version": "0.9", "accepted": True},
    )
    assert wrong_version.status_code == 409

    accepted = _accept_consent(client)
    assert accepted["term"]["accepted"] is True
    assert accepted["term"]["accepted_at"]
    assert accepted["enrollment"]["can_capture"] is True

    repeated = _accept_consent(client)
    assert repeated["term"]["accepted"] is True

    from app.database import SessionLocal
    from app.models import AuditLog, FaceConsent

    db = SessionLocal()
    try:
        consents = db.scalars(select(FaceConsent)).all()
        assert any(item.term_version == "1.0" for item in consents)
        actions = db.scalars(select(AuditLog.action)).all()
        assert "consentimento_facial_aceito" in actions
    finally:
        db.close()


def test_face_enrollment_samples_limit_and_reset(client, fake_face_service):
    _create_employee(client)
    blocked = _upload_sample(client)
    assert blocked.status_code == 403

    _accept_consent(client)

    invalid_type = _upload_sample(client, content_type="text/plain")
    assert invalid_type.status_code == 415

    first = _upload_sample(client)
    assert first.status_code == 201, first.text
    assert first.json()["sample"]["index"] == 1
    assert first.json()["status"]["enrollment"]["samples"] == 1
    assert first.json()["status"]["enrollment"]["complete"] is False

    different = _upload_sample(client, b"different-person")
    assert different.status_code == 422
    assert "mesma pessoa" in different.json()["detail"]
    assert client.get("/api/face/status").json()["enrollment"]["samples"] == 1

    second = _upload_sample(client, b"second-image")
    third = _upload_sample(client, b"third-image")
    assert second.status_code == 201
    assert third.status_code == 201
    complete = third.json()["status"]["enrollment"]
    assert complete["samples"] == 3
    assert complete["complete"] is True
    assert complete["can_capture"] is False
    assert client.get("/api/auth/me").json()["user"]["face_enrolled"] is True

    extra = _upload_sample(client)
    assert extra.status_code == 409
    assert "concluído" in extra.json()["detail"]

    reset = client.delete(
        "/api/face/enrollment",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert reset.status_code == 200
    assert reset.json()["embeddings_removed"] == 3
    assert reset.json()["status"]["enrollment"]["samples"] == 0
    assert reset.json()["status"]["term"]["accepted"] is True
    assert client.get("/api/auth/me").json()["user"]["face_enrolled"] is False


def test_face_consent_revoke_deletes_biometric_data(client, fake_face_service):
    _create_employee(client)
    _accept_consent(client)
    assert _upload_sample(client, b"one").status_code == 201
    assert _upload_sample(client, b"two").status_code == 201
    assert _upload_sample(client, b"three").status_code == 201
    user_id = client.get("/api/auth/me").json()["user"]["id"]

    revoked = client.delete(
        "/api/face/consent",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert revoked.status_code == 200, revoked.text
    body = revoked.json()
    assert body["embeddings_removed"] == 3
    assert body["status"]["term"]["accepted"] is False
    assert body["status"]["enrollment"]["samples"] == 0
    assert body["status"]["enrollment"]["complete"] is False
    assert client.get("/api/auth/me").json()["user"]["face_enrolled"] is False

    from app.database import SessionLocal
    from app.models import AuditLog, FaceConsent, FaceEmbedding

    db = SessionLocal()
    try:
        assert not db.scalars(
            select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
        ).all()
        assert not db.scalars(select(FaceConsent).where(FaceConsent.user_id == user_id)).all()
        actions = db.scalars(select(AuditLog.action)).all()
        assert "consentimento_facial_revogado" in actions
    finally:
        db.close()

    blocked_again = _upload_sample(client)
    assert blocked_again.status_code == 403


def test_face_enrollment_maps_quality_and_model_errors(client, monkeypatch):
    _create_employee(client)
    _accept_consent(client)

    class QualityFailure:
        loaded = False

        def analyze(self, _data: bytes):
            raise FaceQualityError("Nenhum rosto encontrado.", code="rosto_nao_encontrado")

    monkeypatch.setattr("app.routers.face.get_face_service", QualityFailure)
    quality_failure = _upload_sample(client)
    assert quality_failure.status_code == 422
    assert "Nenhum rosto" in quality_failure.json()["detail"]

    class ModelFailure:
        loaded = False

        def analyze(self, _data: bytes):
            raise FaceServiceUnavailable("Modelo facial indisponível.")

    monkeypatch.setattr("app.routers.face.get_face_service", ModelFailure)
    model_failure = _upload_sample(client)
    assert model_failure.status_code == 503
    assert "indisponível" in model_failure.json()["detail"]


def test_face_routes_require_password_change_completion(client):
    _login_rh(client)
    options = client.get("/api/rh/options").json()
    suffix = _suffix()
    created = client.post(
        "/api/rh/people",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "name": "Acesso Facial Pendente",
            "email": f"m3.pendente.{suffix}@lins.local",
            "role": "funcionario",
            "leader_id": options["leaders"][0]["id"],
        },
    )
    assert created.status_code == 201
    response = login(
        client,
        f"m3.pendente.{suffix}@lins.local",
        created.json()["temporary_password"],
    )
    assert response.status_code == 200
    blocked = client.get("/api/face/term")
    assert blocked.status_code == 403
    assert blocked.headers.get("X-Next-Step") == "/trocar-senha"
