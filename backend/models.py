from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 1. Basic Data
    region = Column(String)
    location = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    duration_days = Column(Integer)
    event_time = Column(String)
    area_size = Column(Float)
    is_free = Column(Boolean)
    expected_budget = Column(Float)
    actual_budget = Column(Float, nullable=True)
    promo_budget = Column(Float)
    staff_count = Column(Integer)
    volunteer_count = Column(Integer)

    # 2. Performance Data
    total_visitors = Column(Integer, nullable=True)
    daily_visitors = Column(Integer, nullable=True)
    revenue = Column(Float, nullable=True)
    economic_effect = Column(Float, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    revisit_rate = Column(Float, nullable=True)

    # 3. Regional Data
    population = Column(Integer, nullable=True)
    tourist_count = Column(Integer, nullable=True)
    foreign_visitors = Column(Integer, nullable=True)

    # 4. Access Data
    public_transport_access = Column(Float, nullable=True)
    parking_capacity = Column(Integer, nullable=True)
    lodging_count = Column(Integer, nullable=True)

    # 5. Weather Data
    avg_temp = Column(Float, nullable=True)
    rain_prob = Column(Float, nullable=True)

    # 6. Content Data
    program_count = Column(Integer, nullable=True)
    has_experience = Column(Boolean, default=False)
    has_food = Column(Boolean, default=False)
    has_celebrity = Column(Boolean, default=False)

    # 7. Online Interest
    search_volume = Column(Integer, nullable=True)
    sns_mentions = Column(Integer, nullable=True)

    # 8. Operations Data
    toilets_count = Column(Integer, nullable=True)
    police_count = Column(Integer, nullable=True)
    medical_staff_count = Column(Integer, nullable=True)

    analysis = relationship("AnalysisResult", back_populates="project", uselist=False)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    predicted_visitors = Column(Integer)
    success_probability = Column(Float)

    # Storing JSON strings for complex outputs
    feature_importance = Column(String) # JSON string
    generated_plan = Column(String) # JSON string

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("Project", back_populates="analysis")
