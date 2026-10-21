from __future__ import annotations

import re

from app.security import (
    generate_certificate_code,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)


def test_password_hash_round_trip():
    password_hash = hash_password("SenhaSegura@2026")
    assert password_hash.startswith("$argon2")
    assert verify_password(password_hash, "SenhaSegura@2026")
    assert not verify_password(password_hash, "SenhaErrada@2026")
    assert not needs_rehash(password_hash)


def test_password_strength_rules():
    assert validate_password_strength("Senha@2026") == []
    errors = validate_password_strength("fraca")
    assert any("8 caracteres" in error for error in errors)
    assert any("maiúscula" in error for error in errors)
    assert any("número" in error for error in errors)


def test_certificate_code_format_is_unique():
    codes = {generate_certificate_code() for _ in range(100)}
    assert len(codes) == 100
    assert all(re.fullmatch(r"LINS-[A-Z2-9]{5}-[A-Z2-9]{5}-[A-Z2-9]{5}", code) for code in codes)
