"""비밀번호 해시 + JWT. (표준 pbkdf2 사용 — 외부 라이브러리 의존 없음)"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt

from app.config import settings

_ITER = 200_000


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), _ITER).hex()
    return f"pbkdf2_sha256${_ITER}${salt}${dk}"


def verify_password(pw: str, hashed: str) -> bool:
    try:
        _, iters, salt, dk = hashed.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), int(iters)).hex()
        return hmac.compare_digest(calc, dk)
    except (ValueError, AttributeError):
        return False


def create_access_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MIN),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> str | None:
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return data.get("sub")
    except jwt.PyJWTError:
        return None
