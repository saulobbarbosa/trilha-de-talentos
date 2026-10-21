from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
TEST_DB_NAME = f"test_app_{uuid.uuid4().hex}.db"
TEST_DB_PATH = ROOT / "data" / TEST_DB_NAME

os.environ["DATABASE_URL"] = f"sqlite:///./data/{TEST_DB_NAME}"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest-1234567890"
os.environ["DEV_MODE"] = "true"
os.environ["FACE_MODEL_PRELOAD"] = "false"
os.environ["SESSION_COOKIE_SECURE"] = "false"

from app.database import SessionLocal, engine, init_db  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402

TEST_USERS = [
    {
        "name": "RH Teste",
        "email": "teste.rh@lins.local",
        "password": "TesteRh@2026",
        "role": Role.RH.value,
        "must_change_password": False,
    },
    {
        "name": "Líder Teste",
        "email": "teste.lider@lins.local",
        "password": "TesteLider@2026",
        "role": Role.LIDER.value,
        "must_change_password": False,
    },
    {
        "name": "Instrutor Teste",
        "email": "teste.instrutor@lins.local",
        "password": "TesteInstrutor@2026",
        "role": Role.INSTRUTOR.value,
        "must_change_password": False,
    },
    {
        "name": "Funcionário Teste",
        "email": "teste.funcionario@lins.local",
        "password": "TesteFuncionario@2026",
        "role": Role.FUNCIONARIO.value,
        "must_change_password": False,
    },
    {
        "name": "Primeiro Acesso Teste",
        "email": "teste.primeiro.acesso@lins.local",
        "password": "Temporaria@2026",
        "role": Role.FUNCIONARIO.value,
        "must_change_password": True,
    },
]


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    init_db()
    db = SessionLocal()
    try:
        for data in TEST_USERS:
            exists = db.scalar(select(User).where(User.email == data["email"]))
            if exists:
                continue
            db.add(
                User(
                    name=data["name"],
                    email=data["email"],
                    password_hash=hash_password(data["password"]),
                    role=data["role"],
                    must_change_password=data["must_change_password"],
                    face_enrolled=False,
                    is_active=True,
                )
            )
        db.commit()
    finally:
        db.close()

    yield

    engine.dispose()
    for path in (TEST_DB_PATH, Path(f"{TEST_DB_PATH}-wal"), Path(f"{TEST_DB_PATH}-shm")):
        path.unlink(missing_ok=True)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
