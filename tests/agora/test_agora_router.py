from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routers.agora import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_router_health():
    response = client.get("/agora/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "AGORA"}

def test_router_markets():
    response = client.get("/agora/markets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_router_pulse_invalid_horizon():
    response = client.get("/agora/pulse?market=m&product=p&subfamily=s&horizon=5")
    assert response.status_code == 400
    assert "Horizonte inválido" in response.json()["detail"]

def test_router_pulse_ok():
    response = client.get("/agora/pulse?market=chile_construccion&product=tubo_pvc&subfamily=pvc_sanitario&horizon=6")
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "AGORA"
    assert data["projection"]["horizon_months"] == 6
