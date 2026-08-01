"""공통 의존성 — 현재 사용자."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token


def current_user(authorization: str = Header(default=""),
                 db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증 토큰이 필요합니다.")
    email = decode_token(authorization.split(" ", 1)[1])
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "사용자를 찾을 수 없습니다.")
    return user
