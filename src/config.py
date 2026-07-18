"""프로젝트 공통 설정 · 경로 · API 키 로딩.

모든 스크립트/노트북에서 `from src.config import ...` 로 재사용한다.
API 키는 .env 파일에서 읽으며, git 에는 절대 커밋하지 않는다(.gitignore 참고).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# --- 경로 ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

for _d in (RAW_DIR, PROCESSED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- API 키 (.env 에서 로드) ---
load_dotenv(ROOT_DIR / ".env")

TOURAPI_SERVICE_KEY = os.getenv("TOURAPI_SERVICE_KEY", "")
KMA_SERVICE_KEY = os.getenv("KMA_SERVICE_KEY", "")


def require_key(name: str, value: str) -> str:
    """키가 비어 있으면 친절한 에러를 낸다."""
    if not value:
        raise RuntimeError(
            f"환경변수 {name} 가 설정되지 않았습니다. "
            f".env.example 을 .env 로 복사한 뒤 키를 입력하세요."
        )
    return value
