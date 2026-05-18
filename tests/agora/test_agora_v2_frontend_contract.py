from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routers.agora_v2 import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_markets_contract():
    response = client.get("/agora/v2/markets")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert len(data) > 0
    m = data[0]
    required_fields = ["id", "safe_id", "market_id", "safe_market_id", "name", "frontend_label", "active"]
    for field in required_fields:
        assert field in m, f"Missing field {field} in market response"
    assert m["active"] is True

def test_products_contract():
    response = client.get("/agora/v2/products?market_id=mercado_sanitario_hidraulico")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    p = data[0]
    required_fields = ["id", "safe_id", "product_id", "safe_product_id", "market_id", "safe_market_id", "name", "product_nombre", "frontend_label", "families_count", "active"]
    for field in required_fields:
        assert field in p, f"Missing field {field} in product response"
    assert p["families_count"] > 0

def test_families_contract():
    response = client.get("/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    f = data[0]
    required_fields = ["family_id", "safe_id", "safe_family_id", "family_nombre", "frontend_label", "product_id", "safe_product_id", "data_status"]
    for field in required_fields:
        assert field in f, f"Missing field {field} in family response"
    assert f["data_status"] in ["real_available", "sample_available", "fallback_available", "no_data"]

def test_pulse_contract_with_sample():
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6"
    response = client.get(url)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    
    # Validar campos raiz
    required_pulse_fields = [
        "module", "api_version", "market_id", "safe_market_id", "product_id", "safe_product_id", 
        "family_id", "safe_family_id", "history_window_months", "projection_horizon_months", 
        "observation", "projection", "economic_indicators", "market_forces", "margin_reference", 
        "commercial_interpretation", "cfg_context", "snapshot_context", "warnings", 
        "frontend_message", "data_status", "snapshot_status", "source_context"
    ]
    for field in required_pulse_fields:
        assert field in data, f"Missing pulse field: {field}"
        
    assert data["data_status"] == "sample_available"
    assert data["snapshot_status"] == "sample_snapshot"
    assert data["source_context"]["source_mode"] == "sample"
    assert data["source_context"]["real_web_observation"] is False
    assert data["source_context"]["is_sample_data"] is True
    assert data["source_context"]["display_as_reference_only"] is True
    assert data["frontend_message"] != ""
    assert len(data["warnings"]) > 0

def test_pulse_contract_family_without_snapshot():
    # Familia en catalogo pero no en snapshots sample
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_codos_pvc_sanitario&horizon=6"
    response = client.get(url)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    
    # Debe ser fallback_available segun agora_v2_service.py
    assert data["data_status"] == "fallback_available"
    assert data["snapshot_status"] in ["missing_snapshot", "fallback_snapshot"]
    assert data["source_context"]["source_mode"] == "fallback"
    assert data["source_context"]["real_web_observation"] is False
    assert "No existe snapshot" in data["warnings"][0]
    assert "referenciales" in data["frontend_message"]

def test_frontend_friendly_errors():
    # Market not found
    response = client.get("/agora/v2/products?market_id=mercado_inexistente")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "MARKET_NOT_FOUND"
    assert "suggestion" in detail

    # Product not found
    response = client.get("/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=producto_inexistente")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "PRODUCT_NOT_FOUND"

    # Family not found
    response = client.get("/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=familia_inexistente&horizon=6")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "FAMILY_NOT_FOUND"

    # Invalid horizon
    response = client.get("/agora/v2/pulse?market_id=m&product_id=p&family_id=f&horizon=5")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "INVALID_HORIZON"
    assert detail["allowed_values"] == [3, 6, 12]

def test_safe_ids_resolution():
    # canónico con tildes
    url_can = "/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberías_y_fittings_pvc_sanitario"
    # safe sin tildes
    url_safe = "/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario"
    
    resp_can = client.get(url_can)
    resp_safe = client.get(url_safe)
    
    assert resp_can.status_code == 200
    assert resp_safe.status_code == 200
    assert resp_can.json() == resp_safe.json()
