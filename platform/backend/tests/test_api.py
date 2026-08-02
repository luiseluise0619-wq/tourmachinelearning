"""API 통합 테스트 — 인증·프로젝트·AI 예측·생성·PDF 전 플로우."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_auth_flow(client):
    # 중복 가입 차단
    client.post("/api/auth/register", json={"email": "dup@x.com", "password": "pw123456"})
    r = client.post("/api/auth/register", json={"email": "dup@x.com", "password": "pw123456"})
    assert r.status_code == 409
    # 로그인
    r = client.post("/api/auth/login", json={"email": "dup@x.com", "password": "pw123456"})
    assert r.status_code == 200 and "access_token" in r.json()
    # 잘못된 비밀번호
    r = client.post("/api/auth/login", json={"email": "dup@x.com", "password": "wrong"})
    assert r.status_code == 401


def test_auth_required(client):
    assert client.get("/api/projects").status_code == 401


def test_project_and_festival_crud(client, auth, sample_festival):
    pid = client.post("/api/projects", json={"name": "테스트 프로젝트"}, headers=auth).json()["id"]
    assert pid
    assert any(p["id"] == pid for p in client.get("/api/projects", headers=auth).json())
    r = client.post(f"/api/projects/{pid}/festivals", json=sample_festival, headers=auth)
    assert r.status_code == 200
    assert len(client.get(f"/api/projects/{pid}/festivals", headers=auth).json()) >= 1


def test_predict(client, auth, sample_festival):
    r = client.post("/api/ai/predict", json={"festival": sample_festival}, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["expected_visitors"] > 0
    assert 0 <= d["success_probability"] <= 1
    assert 0 <= d["appeal_score"] <= 100
    assert len(d["top_factors"]) == 5
    assert isinstance(d["feedback"], list)
    assert d["interval_80"][0] <= d["interval_80"][1]


def test_success_analysis(client, auth, sample_festival):
    d = client.post("/api/ai/success", json={"festival": sample_festival}, headers=auth).json()
    assert "success_score" in d and "recommendations" in d


def test_generate_fallback(client, auth):
    d = client.post("/api/ai/generate",
                    json={"budget_mil_won": 500, "target_audience": "20대",
                          "region": "서울 근교", "theme": "야간 뮤직"}, headers=auth).json()
    assert "concept" in d and len(d.get("programs", [])) > 0
    assert "budget_allocation" in d


def test_pdf_export(client, auth, sample_festival):
    r = client.post("/api/reports/pdf", json={"festival": sample_festival}, headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000


def test_csv_upload(client, auth):
    pid = client.post("/api/projects", json={"name": "CSV 테스트"}, headers=auth).json()["id"]
    csv = "name,region,duration_days,budget_mil_won,visitors_total\n벚꽃축제,서울,3,300,50000\n"
    r = client.post(f"/api/projects/{pid}/festivals/upload-csv",
                    files={"file": ("f.csv", csv, "text/csv")}, headers=auth)
    assert r.status_code == 200 and r.json()["inserted"] == 1
