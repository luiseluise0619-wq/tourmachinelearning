from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FestCast API"}

def test_create_and_analyze_project():
    payload = {
        "name": "Test Festival",
        "region": "Seoul",
        "location": "Park",
        "start_date": "2024-05-01",
        "end_date": "2024-05-03",
        "duration_days": 3,
        "event_time": "10:00-22:00",
        "area_size": 20000.0,
        "is_free": True,
        "expected_budget": 50000000.0,
        "promo_budget": 5000000.0,
        "staff_count": 50,
        "volunteer_count": 30
    }

    # Create Project
    response = client.post("/api/festivals", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Festival"
    project_id = data["id"]

    # Analyze Project
    analyze_res = client.post(f"/api/festivals/{project_id}/analyze")
    assert analyze_res.status_code == 200
    analysis_data = analyze_res.json()
    assert "predicted_visitors" in analysis_data
    assert "success_probability" in analysis_data
    assert "feature_importance" in analysis_data
    assert "generated_plan" in analysis_data
