import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routers.agora_v2 import router
from backend.api.security.deps import get_current_claims
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

# Mock para suscripción y claims
def get_mock_claims_basic():
    return {"user_id": "1", "plan": "basic"}

def get_mock_claims_pro():
    return {"user_id": "1", "plan": "pro"}

def get_mock_claims_enterprise():
    return {"user_id": "1", "plan": "enterprise"}

app = FastAPI()
app.include_router(router)

@pytest.fixture
def client_basic():
    app.dependency_overrides[get_current_claims] = get_mock_claims_basic
    with TestClient(app) as c:
        yield c

@pytest.fixture
def client_pro():
    app.dependency_overrides[get_current_claims] = get_mock_claims_pro
    with TestClient(app) as c:
        yield c

@pytest.fixture
def client_enterprise():
    app.dependency_overrides[get_current_claims] = get_mock_claims_enterprise
    with TestClient(app) as c:
        yield c

def test_pulse_root_fields(client_pro):
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6"
    response = client_pro.get(url)
    assert response.status_code == 200
    data = response.json()
    
    # Bloqueador 1: Campos raíz garantizados
    assert "agora_enabled" in data
    assert "plan_tier" in data
    assert "feature_depth" in data
    assert "data_mode" in data
    assert "history_status" in data
    assert "available_months" in data
    assert "required_months" in data
    assert "projection_quality" in data
    assert "allowed_horizons" in data
    assert "requested_horizon" in data
    assert "effective_horizon" in data
    assert "horizon_adjusted" in data
    assert "user_message" in data
    assert "commercial_position" in data
    assert data["commercial_position"] is not None

def test_commercial_position_always_present(client_pro):
    # Sin costos ni precios
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6"
    response = client_pro.get(url)
    data = response.json()
    cp = data["commercial_position"]
    assert cp is not None
    assert cp["current_cost"] is None
    assert cp["current_sale_price"] is None
    assert cp["market_position_now"] == "unavailable"

def test_market_position_engine_formulas(client_pro):
    # Caso controlado: 
    # market_ref (tubos pvc) suele ser ~4390 en sample snapshots
    # current_cost=3000, current_sale_price=5000
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6&current_cost=3000&current_sale_price=5000"
    response = client_pro.get(url)
    data = response.json()
    cp = data["commercial_position"]
    
    # current_margin_pct = (5000 - 3000) / 5000 = 0.4 (40%)
    assert cp["current_margin_pct"] == pytest.approx(0.4)
    assert cp["margin_status"] == "healthy"
    
    # market_ref ~ 4390
    # price_gap_pct = (5000 - 4390) / 4390 ~ 0.138
    assert cp["price_gap_pct"] > 0.05
    assert cp["market_position_now"] == "above_market"

def test_plan_basic_clipping(client_basic):
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=12"
    response = client_basic.get(url)
    data = response.json()
    
    # Ajuste de horizonte
    assert data["effective_horizon"] == 3
    assert data["horizon_adjusted"] is True
    assert data["allowed_horizons"] == [3]
    
    # Clipping en commercial_position
    cp = data["commercial_position"]
    assert cp["projected_market_price"] is None
    assert cp["market_position_projected"] == "unavailable"
    assert cp["commercial_risk"] == "unavailable"

def test_zero_division_safety(client_pro):
    # current_sale_price = 0
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6&current_sale_price=0&current_cost=1000"
    response = client_pro.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["commercial_position"]["current_margin_pct"] is None

def test_meli_403_handling():
    from backend.agora.price_intelligence.source_clients.mercado_libre_client import MercadoLibreClient
    import httpx
    from unittest.mock import AsyncMock
    
    client = MercadoLibreClient()
    
    # Mock de httpx para devolver 403
    mock_res = MagicMock()
    mock_res.status_code = 403
    
    with patch("httpx.AsyncClient.get", return_value=mock_res):
        import asyncio
        res = asyncio.run(client.search_items(MagicMock(), "test"))
        assert res["status"] == "forbidden"
        assert res["http_status"] == 403
        assert res["items"] == []

def test_no_regression_core_models():
    # Verificar que no hayamos tocado archivos de modelos core (revisión de estructura)
    import os
    assert os.path.exists("backend/models/epsilon/EPSILON_SERVICE.py")
    assert os.path.exists("backend/models/sigma/SIGMA_SERVICE.py")
    assert os.path.exists("backend/models/poseidon/POSEIDON_SERVICE.py")
