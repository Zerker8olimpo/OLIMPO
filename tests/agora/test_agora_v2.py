from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routers.agora_v2 import router
from backend.agora.compatibility_alias_adapter import CompatibilityAliasAdapter

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_v2_health():
    response = client.get("/agora/v2/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "AGORA_V2", "architecture": "canonical"}

def test_v2_markets():
    response = client.get("/agora/v2/markets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_v2_products():
    response = client.get("/agora/v2/products?market_id=mercado_sanitario_hidraulico")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_v2_families():
    response = client.get("/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberías_y_fittings_pvc_sanitario")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_v2_pulse_invalid_horizon():
    response = client.get("/agora/v2/pulse?market_id=m&product_id=p&family_id=f&horizon=5")
    assert response.status_code == 400

def test_alias_adapter():
    adapter = CompatibilityAliasAdapter()
    m, p, f = adapter.resolve_legacy_to_canonical("chile_construccion", "tubo_pvc", "pvc_sanitario")
    assert m == "mercado_sanitario_hidraulico"
    assert p == "tuberías_y_fittings_pvc_sanitario"
    assert f == "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario"
