"""환경 설정. DB/키 없어도 동작하도록 안전한 기본값."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # DB: 미설정 시 로컬 SQLite 자동
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./festcast.db")
    # 인증
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MIN: int = int(os.getenv("JWT_EXPIRE_MIN", "1440"))
    # LLM (없으면 규칙 기반 폴백)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "").lower()  # openai | gemini | ""
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
