from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, next_step_for, serialize_user
from app.models import User, utcnow
from app.security import (
    clear_session_cookie,
    client_ip,
    ensure_csrf_cookie,
    generate_temp_password,
    hash_password,
    login_limiter,
    needs_rehash,
    require_csrf,
    set_session_cookie,
    validate_password_strength,
    verify_password,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["autenticacao"])
settings = get_settings()

DUMMY_HASH = hash_password(generate_temp_password(24))


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Informe um e-mail válido.")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.get("/csrf")
def csrf(request: Request, response: Response) -> dict:
    token = ensure_csrf_cookie(request, response)
    return {"csrf_token": token, "dev_mode": settings.dev_mode}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    ip = client_ip(request)
    attempt_key = f"{ip}:{payload.email}"
    login_limiter.check(attempt_key)

    user = db.scalar(select(User).where(User.email == payload.email))
    password_ok = verify_password(user.password_hash if user else DUMMY_HASH, payload.password)

    if not user or not password_ok or not user.is_active:
        login_limiter.fail(attempt_key)
        if user:
            log_action(
                db,
                actor_id=user.id,
                action="login_falhou",
                entity="user",
                entity_id=user.id,
                ip_address=ip,
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )

    login_limiter.reset(attempt_key)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = utcnow()
    log_action(
        db,
        actor_id=user.id,
        action="login",
        entity="user",
        entity_id=user.id,
        ip_address=ip,
    )
    db.commit()
    db.refresh(user)

    set_session_cookie(response, user.id)
    ensure_csrf_cookie(request, response)
    return {"user": serialize_user(user), "next_step": next_step_for(user)}


@router.get("/me")
def me(request: Request, response: Response, user: User = Depends(get_current_user)) -> dict:
    ensure_csrf_cookie(request, response)
    return {
        "user": serialize_user(user),
        "next_step": next_step_for(user),
        "dev_mode": settings.dev_mode,
    }


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    log_action(db, actor_id=user.id, action="logout", entity="user", entity_id=user.id)
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    if not verify_password(user.password_hash, payload.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha atual não confere.",
        )
    errors = validate_password_strength(payload.new_password)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=" ".join(errors))
    if verify_password(user.password_hash, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha não pode ser igual à senha atual/temporária.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    log_action(
        db,
        actor_id=user.id,
        action="senha_alterada",
        entity="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return {"user": serialize_user(user), "next_step": next_step_for(user)}
