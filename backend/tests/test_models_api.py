import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.inference_service import inference_service

client = TestClient(app)

def test_model_status():
    response = client.get("/api/v1/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert data["model_name"] == "FOD_Karhtikeyan.pt"
    assert data["status"] in ["READY", "RUNNING"]
    assert "classes" in data
    # FOD class should be dynamically present
    assert any("FOD" in str(val) for val in data["classes"].values())
    assert data["is_valid"] is True
    assert "device" in data

def test_model_list():
    response = client.get("/api/v1/models/list")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    model_names = [m["model_name"] for m in models]
    assert "FOD_Karhtikeyan.pt" in model_names

    # Check active model flag
    active_models = [m for m in models if m["is_active"]]
    assert len(active_models) >= 1
    assert active_models[0]["model_name"] == "FOD_Karhtikeyan.pt"

def test_model_select_valid():
    # Test selecting available model
    response = client.post("/api/v1/models/select", json={"model": "best.pt"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["model"] == "best.pt"
    assert data["status"] == "READY"

    # Switch back to default FOD model
    response_fod = client.post("/api/v1/models/select", json={"model": "FOD_Karhtikeyan.pt"})
    assert response_fod.status_code == 200
    data_fod = response_fod.json()
    assert data_fod["success"] is True
    assert data_fod["model"] == "FOD_Karhtikeyan.pt"
    assert data_fod["status"] == "READY"
    assert any("FOD" in str(val) for val in data_fod["classes"].values())

def test_model_select_invalid():
    response = client.post("/api/v1/models/select", json={"model": "non_existent_model_xyz.pt"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
