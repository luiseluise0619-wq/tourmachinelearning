"""테스트 픽스처 — 격리된 임시 SQLite로 앱을 띄운다."""
import os
import tempfile

# 앱 import 전에 DB를 임시 파일로 지정 (실 DB 오염 방지)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:      # lifespan 실행 → 테이블 생성
        yield c


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/api/auth/register",
                    json={"email": "tester@festcast.ai", "password": "pw123456",
                          "name": "테스터", "org": "○○시청"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def sample_festival():
    return {
        "name": "테스트 가을축제", "region": "경기",
        "start_date": "2026-10-17", "end_date": "2026-10-19",
        "duration_days": 3, "budget_mil_won": 500, "is_free": True,
        "content": {"num_programs": 8, "performance": True, "food": True,
                    "experience": True, "celebrity": True},
        "operations": {"capacity": 80000},
    }
