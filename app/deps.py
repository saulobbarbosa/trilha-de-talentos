from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.security import read_session_user_id


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = read_session_user_id(request)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada ou inexistente. Faça login novamente.",
        )
    return user


def get_onboarded_user(user: User = Depends(get_current_user)) -> User:
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Troca de senha obrigatória antes de continuar.",
            headers={"X-Next-Step": "/trocar-senha"},
        )
    return user


def require_roles(*roles: Role | str) -> Callable[..., User]:
    allowed = {role.value if isinstance(role, Role) else role for role in roles}

    def dependency(user: User = Depends(get_onboarded_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para acessar este recurso.",
            )
        return user

    return dependency


def home_for_role(role: str) -> str:
    return {
        Role.RH.value: "/rh",
        Role.LIDER.value: "/lider",
        Role.INSTRUTOR.value: "/instrutor",
        Role.FUNCIONARIO.value: "/funcionario",
    }.get(role, "/")


def next_step_for(user: User) -> str:
    if user.must_change_password:
        return "/trocar-senha"
    return home_for_role(user.role)


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "leader_id": user.leader_id,
        "must_change_password": user.must_change_password,
        "face_enrolled": user.face_enrolled,
        "is_active": user.is_active,
    }
