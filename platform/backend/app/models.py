"""ORM 모델 — User · Project · Festival · Analysis.

Festival은 요구된 전 카테고리(기본·성과·지역·접근성·날씨·콘텐츠·온라인·운영)를
JSON 필드로 유연하게 담아 실데이터 교체·확장이 쉽도록 설계한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(120))
    org = Column(String(200))              # 소속 지자체/기관
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    festivals = relationship("Festival", back_populates="project", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="project", cascade="all, delete-orphan")


class Festival(Base):
    """축제 기획/성과 데이터. 핵심 필드 + 카테고리별 JSON 확장."""
    __tablename__ = "festivals"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    # 자주 쓰는 핵심 필드(쿼리·모델 입력)
    name = Column(String(300), nullable=False)
    region = Column(String(50))
    place = Column(String(300))
    start_date = Column(String(10))        # YYYY-MM-DD
    end_date = Column(String(10))
    duration_days = Column(Integer)
    is_free = Column(Integer, default=1)
    budget_mil_won = Column(Float)         # 예산(백만원)
    visitors_total = Column(Integer)       # 실적(있으면)
    # 전 카테고리 원본을 유연 저장
    basic = Column(JSON, default=dict)     # 기본(면적·시간·인력·자원봉사 등)
    performance = Column(JSON, default=dict)   # 성과(일별·매출·만족도·SNS 등)
    region_data = Column(JSON, default=dict)   # 지역(인구·소득·유동·상권 등)
    access = Column(JSON, default=dict)         # 접근성(교통·주차·숙박 등)
    weather = Column(JSON, default=dict)        # 날씨
    content = Column(JSON, default=dict)        # 콘텐츠(공연·출연자·프로그램 등)
    online = Column(JSON, default=dict)         # 온라인 관심(검색·SNS·뉴스 등)
    operations = Column(JSON, default=dict)     # 운영(동선·혼잡·안전 등)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="festivals")


class Analysis(Base):
    """AI 분석 실행 기록(예측·성공진단·생성기획)."""
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    festival_id = Column(Integer, ForeignKey("festivals.id"), nullable=True)
    kind = Column(String(30))              # predict | success | generate
    inputs = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="analyses")
