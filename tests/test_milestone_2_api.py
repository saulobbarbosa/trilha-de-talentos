from __future__ import annotations

import uuid
from datetime import date, timedelta

from tests.helpers import csrf_token, login


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _login_rh(client):
    response = login(client, "teste.rh@lins.local", "TesteRh@2026")
    assert response.status_code == 200
    return response


def _login_leader(client):
    response = login(client, "teste.lider@lins.local", "TesteLider@2026")
    assert response.status_code == 200
    return response


def _options(client) -> dict:
    response = client.get("/api/rh/options")
    assert response.status_code == 200
    return response.json()


def _create_person(client, *, name: str, email: str, leader_id: int | None, role: str = "funcionario"):
    payload = {"name": name, "email": email, "role": role, "leader_id": leader_id}
    response = client.post(
        "/api/rh/people",
        headers={"X-CSRF-Token": csrf_token(client)},
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_training(client, *, instructor_id: int, seats: int = 3, title: str | None = None):
    suffix = _suffix()
    payload = {
        "title": title or f"Treinamento M2 {suffix}",
        "description": "Turma criada pelos testes automatizados do Marco 2.",
        "instructor_id": instructor_id,
        "date": (date.today() + timedelta(days=30)).isoformat(),
        "start_time": "08:00",
        "end_time": "12:00",
        "location": "Sala de treinamento",
        "seats": seats,
        "workload_hours": 4,
    }
    response = client.post(
        "/api/rh/trainings",
        headers={"X-CSRF-Token": csrf_token(client)},
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()["training"]


def test_rh_people_crud_reset_password_and_outbox(client):
    _login_rh(client)
    leader_id = _options(client)["leaders"][0]["id"]
    suffix = _suffix()
    email = f"m2.pessoa.{suffix}@lins.local"

    created = _create_person(
        client,
        name="Pessoa M2",
        email=email,
        leader_id=leader_id,
    )
    first_password = created["temporary_password"]
    person_id = created["person"]["id"]
    assert created["person"]["must_change_password"] is True
    assert created["person"]["leader_id"] == leader_id
    assert len(first_password) >= 10

    people = client.get("/api/rh/people").json()["people"]
    assert any(person["id"] == person_id for person in people)

    updated = client.patch(
        f"/api/rh/people/{person_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"name": "Pessoa M2 Atualizada"},
    )
    assert updated.status_code == 200
    assert updated.json()["person"]["name"] == "Pessoa M2 Atualizada"

    reset = client.post(
        f"/api/rh/people/{person_id}/reset-password",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert reset.status_code == 200
    second_password = reset.json()["temporary_password"]
    assert second_password != first_password

    outbox = client.get("/api/rh/outbox").json()["emails"]
    recipient_emails = [item for item in outbox if item["recipient"] == email]
    subjects = {item["subject"] for item in recipient_emails}
    assert "Seu acesso ao Trilha de Talentos" in subjects
    assert "Nova senha temporária - Trilha de Talentos" in subjects
    assert any(first_password in item["body"] for item in recipient_emails)
    assert any(second_password in item["body"] for item in recipient_emails)

    fresh_client_password = login(client, email, second_password)
    assert fresh_client_password.status_code == 200
    assert fresh_client_password.json()["next_step"] == "/trocar-senha"

    _login_rh(client)
    deactivated = client.patch(
        f"/api/rh/people/{person_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["person"]["is_active"] is False


def test_rh_training_crud_and_validation(client):
    _login_rh(client)
    instructor_id = _options(client)["instructors"][0]["id"]
    training = _create_training(client, instructor_id=instructor_id, seats=2)
    training_id = training["id"]
    assert training["status"] == "agendado"
    assert training["instructor_id"] == instructor_id

    updated = client.patch(
        f"/api/rh/trainings/{training_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"seats": 4, "workload_hours": 6},
    )
    assert updated.status_code == 200
    assert updated.json()["training"]["seats"] == 4
    assert updated.json()["training"]["workload_hours"] == 6

    listed = client.get("/api/rh/trainings").json()["trainings"]
    assert any(item["id"] == training_id and item["seats"] == 4 for item in listed)

    disposable = _create_training(client, instructor_id=instructor_id, seats=1)
    deleted = client.delete(
        f"/api/rh/trainings/{disposable['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert deleted.status_code == 200
    listed_after = client.get("/api/rh/trainings").json()["trainings"]
    assert all(item["id"] != disposable["id"] for item in listed_after)

    invalid_date = client.patch(
        f"/api/rh/trainings/{training_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"date": (date.today() - timedelta(days=1)).isoformat()},
    )
    assert invalid_date.status_code == 400
    assert "passado" in invalid_date.json()["detail"]


def test_leader_reserves_and_cancels_team_reservations(client):
    _login_rh(client)
    instructor_id = _options(client)["instructors"][0]["id"]
    leader_id = _options(client)["leaders"][0]["id"]
    suffix = _suffix()
    first = _create_person(
        client,
        name="Colaborador Um",
        email=f"m2.um.{suffix}@lins.local",
        leader_id=leader_id,
    )["person"]
    second = _create_person(
        client,
        name="Colaborador Dois",
        email=f"m2.dois.{suffix}@lins.local",
        leader_id=leader_id,
    )["person"]
    training = _create_training(client, instructor_id=instructor_id, seats=2)

    _login_leader(client)
    page = client.get("/api/leader/reservations").json()
    assert {member["id"] for member in page["team"]} >= {first["id"], second["id"]}

    created = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [first["id"], second["id"]]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["created"] == 2

    page = client.get("/api/leader/reservations").json()
    active = [item for item in page["reservations"] if item["training_id"] == training["id"]]
    assert len(active) == 2
    assert all(item["status"] == "ativa" for item in active)

    training_page = next(item for item in page["trainings"] if item["id"] == training["id"])
    assert set(training_page["team_reserved_ids"]) == {first["id"], second["id"]}
    assert training_page["available"] == 0

    duplicate = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [first["id"]]},
    )
    assert duplicate.status_code == 409
    assert "reserva ativa" in duplicate.json()["detail"].lower()

    reservation_id = active[0]["id"]
    cancelled = client.post(
        f"/api/leader/reservations/{reservation_id}/cancel",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert cancelled.status_code == 200
    repeated = client.post(
        f"/api/leader/reservations/{reservation_id}/cancel",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    assert repeated.status_code == 409

    _login_rh(client)
    outbox = client.get("/api/rh/outbox").json()["emails"]
    subjects = {email["subject"] for email in outbox}
    assert f"Reserva confirmada: {training['title']}" in subjects
    assert f"Reserva cancelada: {training['title']}" in subjects


def test_reservation_capacity_team_scope_and_training_cancel(client):
    _login_rh(client)
    instructor_id = _options(client)["instructors"][0]["id"]
    leader_id = _options(client)["leaders"][0]["id"]
    suffix = _suffix()
    first = _create_person(
        client,
        name="Capacidade Um",
        email=f"m2.cap.um.{suffix}@lins.local",
        leader_id=leader_id,
    )["person"]
    second = _create_person(
        client,
        name="Capacidade Dois",
        email=f"m2.cap.dois.{suffix}@lins.local",
        leader_id=leader_id,
    )["person"]
    training = _create_training(client, instructor_id=instructor_id, seats=1)

    _login_leader(client)
    outsider = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [99999]},
    )
    assert outsider.status_code == 400

    first_booking = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [first["id"]]},
    )
    assert first_booking.status_code == 201

    full = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [second["id"]]},
    )
    assert full.status_code == 409
    assert "Vagas insuficientes" in full.json()["detail"]

    rbac = client.get("/api/rh/people")
    assert rbac.status_code == 403

    _login_rh(client)
    shrink = client.patch(
        f"/api/rh/trainings/{training['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"seats": 1},
    )
    assert shrink.status_code == 200

    cancelled = client.post(
        f"/api/rh/trainings/{training['id']}/cancel",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"reason": "Mudança de agenda"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["cancelled_reservations"] == 1
    assert cancelled.json()["training"]["status"] == "cancelado"

    outbox = client.get("/api/rh/outbox").json()["emails"]
    assert any(
        email["subject"] == f"Treinamento cancelado: {training['title']}"
        and "Mudança de agenda" in email["body"]
        for email in outbox
    )

    _login_leader(client)
    page = client.get("/api/leader/reservations").json()
    reservation = next(
        item
        for item in page["reservations"]
        if item["training_id"] == training["id"] and item["employee_id"] == first["id"]
    )
    assert reservation["status"] == "cancelada"
    assert reservation["training_status"] == "cancelado"

    reopened_booking = client.post(
        "/api/leader/reservations",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"training_id": training["id"], "employee_ids": [first["id"]]},
    )
    assert reopened_booking.status_code == 409
    assert "não está mais aberto" in reopened_booking.json()["detail"]


def test_rh_guards_and_last_rh_protection(client):
    anonymous = client.get("/api/rh/outbox")
    assert anonymous.status_code == 401

    _login_leader(client)
    assert client.get("/api/rh/outbox").status_code == 403
    assert client.get("/api/rh/trainings").status_code == 403

    _login_rh(client)
    me = client.get("/api/auth/me").json()["user"]
    self_deactivate = client.patch(
        f"/api/rh/people/{me['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 400
    assert "própria conta" in self_deactivate.json()["detail"]
