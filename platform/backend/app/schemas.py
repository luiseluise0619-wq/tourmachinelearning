"""Pydantic 스키마 (요청/응답)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, EmailStr


# --- auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    org: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    org: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- project ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# --- festival ---
class FestivalIn(BaseModel):
    name: str
    region: Optional[str] = None
    place: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None
    is_free: Optional[bool] = True
    budget_mil_won: Optional[float] = None
    visitors_total: Optional[int] = None
    basic: dict[str, Any] = {}
    performance: dict[str, Any] = {}
    region_data: dict[str, Any] = {}
    access: dict[str, Any] = {}
    weather: dict[str, Any] = {}
    content: dict[str, Any] = {}
    online: dict[str, Any] = {}
    operations: dict[str, Any] = {}


class FestivalOut(FestivalIn):
    id: int
    project_id: int

    class Config:
        from_attributes = True


# --- AI ---
class PredictRequest(BaseModel):
    festival: FestivalIn


class GenerateRequest(BaseModel):
    budget_mil_won: float
    target_audience: str          # 예: "20대"
    region: str                   # 예: "서울 근교"
    theme: Optional[str] = None
    project_id: Optional[int] = None
