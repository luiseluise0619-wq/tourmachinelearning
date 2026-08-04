from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    region: str
    location: str
    start_date: str
    end_date: str
    duration_days: int
    event_time: str
    area_size: float
    is_free: bool
    expected_budget: float
    actual_budget: Optional[float] = None
    promo_budget: float
    staff_count: int
    volunteer_count: int

    total_visitors: Optional[int] = None
    daily_visitors: Optional[int] = None
    revenue: Optional[float] = None
    economic_effect: Optional[float] = None
    satisfaction_score: Optional[float] = None
    revisit_rate: Optional[float] = None

    population: Optional[int] = None
    tourist_count: Optional[int] = None
    foreign_visitors: Optional[int] = None

    public_transport_access: Optional[float] = None
    parking_capacity: Optional[int] = None
    lodging_count: Optional[int] = None

    avg_temp: Optional[float] = None
    rain_prob: Optional[float] = None

    program_count: Optional[int] = None
    has_experience: Optional[bool] = False
    has_food: Optional[bool] = False
    has_celebrity: Optional[bool] = False

    search_volume: Optional[int] = None
    sns_mentions: Optional[int] = None

    toilets_count: Optional[int] = None
    police_count: Optional[int] = None
    medical_staff_count: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AnalysisResultBase(BaseModel):
    predicted_visitors: int
    success_probability: float
    feature_importance: str # JSON string
    generated_plan: str # JSON string

class AnalysisResultCreate(AnalysisResultBase):
    project_id: int

class AnalysisResult(AnalysisResultBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True
