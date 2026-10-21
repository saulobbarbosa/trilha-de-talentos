from __future__ import annotations

import secrets
import string
import threading
import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
_session_serializer = URLSafeTimedSerializer(settings.secret_key, salt="trilha-talentos-session")

PASSWORD_SPECIAL = "!@#$%&*?-_"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < 8:
        errors.append("A senha deve ter pelo menos 8 caracteres.")
    if len(password) > 128:
        errors.append("A senha deve ter no máximo 128 caracteres.")
    if not any(c.islower() for c in password):
        errors.append("A senha deve conter pelo menos uma letra minúscula.")
    if not any(c.isupper() for c in password):
        errors.append("A senha deve conter pelo menos uma letra maiúscula.")
    if not any(c.isdigit() for c in password):
        errors.append("A senha deve conter pelo menos um número.")
    return errors


def generate_temp_password(length: int = 10) -> str:
    length = max(length, 10)
    alphabet = string.ascii_letters + string.digits + PASSWORD_SPECIAL
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
        ):
            return candidate


def generate_certificate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(15))
    return f"LINS-{raw[0:5]}-{raw[5:10]}-{raw[10:15]}"


def set_session_cookie(response: Response, user_id: int) -> None:
    token = _session_serializer.dumps({"uid": user_id})
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def read_session_user_id(request: Request) -> int | None:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    try:
        payload = _session_serializer.loads(raw, max_age=settings.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    uid = payload.get("uid")
    return uid if isinstance(uid, int) else None


def ensure_csrf_cookie(request: Request, response: Response) -> str:
    token = request.cookies.get(settings.csrf_cookie_name)
    if not token or len(token) < 32:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            key=settings.csrf_cookie_name,
            value=token,
            max_age=settings.session_max_age_seconds,
            httponly=False,
            secure=settings.session_cookie_secure,
            samesite="lax",
            path="/",
        )
    return token


def require_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    header_token = request.headers.get("x-csrf-token", "")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de segurança inválido. Recarregue a página e tente novamente.",
        )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"


@dataclass
class _Attempt:
    failures: int
    window_started: float
    blocked_until: float = 0.0


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, _Attempt] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        expired = [
            key
            for key, attempt in self._attempts.items()
            if now - attempt.window_started > self.window_seconds and attempt.blocked_until < now
        ]
        for key in expired:
            self._attempts.pop(key, None)

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            attempt = self._attempts.get(key)
            if attempt and attempt.blocked_until > now:
                retry = max(1, int(attempt.blocked_until - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Muitas tentativas. Tente novamente em {retry} segundos.",
                    headers={"Retry-After": str(retry)},
                )

    def fail(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempt = self._attempts.get(key)
            if not attempt or now - attempt.window_started > self.window_seconds:
                attempt = _Attempt(failures=0, window_started=now)
                self._attempts[key] = attempt
            attempt.failures += 1
            if attempt.failures >= self.max_attempts:
                attempt.blocked_until = now + self.window_seconds
                attempt.failures = 0
                attempt.window_started = now

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_limiter = LoginRateLimiter(settings.login_max_attempts, settings.login_window_seconds)
