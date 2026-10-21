from __future__ import annotations


def csrf_token(client) -> str:
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    token = response.json()["csrf_token"]
    assert client.cookies.get("tt_csrf") == token
    return token


def login(client, email: str, password: str):
    return client.post(
        "/api/auth/login",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"email": email, "password": password},
    )
