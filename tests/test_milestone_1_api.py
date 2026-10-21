from __future__ import annotations

import pytest

from tests.helpers import csrf_token, login


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_docs_load_with_cdn_allowed_in_dev(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert "https://cdn.jsdelivr.net" in response.headers["content-security-policy"]


def test_protected_home_requires_login(client):
    response = client.get("/api/home")
    assert response.status_code == 401
    assert "Sessão expirada" in response.json()["detail"]


@pytest.mark.parametrize(
    ("email", "password", "role", "home"),
    [
        ("teste.rh@lins.local", "TesteRh@2026", "rh", "/rh"),
        ("teste.lider@lins.local", "TesteLider@2026", "lider", "/lider"),
        ("teste.instrutor@lins.local", "TesteInstrutor@2026", "instrutor", "/instrutor"),
        (
            "teste.funcionario@lins.local",
            "TesteFuncionario@2026",
            "funcionario",
            "/funcionario",
        ),
    ],
)
def test_login_and_role_home(client, email, password, role, home):
    response = login(client, email, password)
    assert response.status_code == 200
    assert response.json()["next_step"] == home
    assert response.json()["user"]["role"] == role

    home_response = client.get("/api/home")
    assert home_response.status_code == 200
    assert home_response.json()["role"] == role
    assert home_response.json()["stats"]


def test_login_rejects_invalid_credentials(client):
    response = login(client, "teste.rh@lins.local", "SenhaIncorreta@2026")
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos."


def test_login_requires_csrf(client):
    csrf_token(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "teste.rh@lins.local", "password": "TesteRh@2026"},
    )
    assert response.status_code == 403
    assert "Token de segurança inválido." in response.json()["detail"]


def test_temporary_password_blocks_home_and_can_be_changed(client):
    response = login(client, "teste.primeiro.acesso@lins.local", "Temporaria@2026")
    assert response.status_code == 200
    assert response.json()["next_step"] == "/trocar-senha"
    assert response.json()["user"]["must_change_password"] is True

    blocked = client.get("/api/home")
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Troca de senha obrigatória antes de continuar."
    assert blocked.headers["X-Next-Step"] == "/trocar-senha"

    changed = client.post(
        "/api/auth/change-password",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "current_password": "Temporaria@2026",
            "new_password": "NovaSenha@2026",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["next_step"] == "/funcionario"
    assert changed.json()["user"]["must_change_password"] is False

    home = client.get("/api/home")
    assert home.status_code == 200
    assert home.json()["role"] == "funcionario"


def test_unknown_certificate_returns_404(client):
    response = client.get("/api/certificates/verify/LINS-AAAAA-AAAAA-AAAAA")
    assert response.status_code == 404
    assert "Certificado não encontrado" in response.json()["detail"]


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/rota-inexistente")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
