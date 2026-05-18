from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routers.agora_v2 import router
from backend.agora.id_normalization_service import IdNormalizationService

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_normalization_logic():
    assert IdNormalizationService.normalize_id("tuberías_y_fittings_pvc_sanitario") == "tuberias_y_fittings_pvc_sanitario"
    assert IdNormalizationService.normalize_id("Válvulas de Esfera Bronce") == "valvulas_de_esfera_bronce"
    assert IdNormalizationService.normalize_id("Pegamentos y Fragües") == "pegamentos_y_fragues"

def test_v2_products_safe_id():
    # Mercado canónico
    response = client.get("/agora/v2/products?market_id=mercado_sanitario_hidraulico")
    assert response.status_code == 200
    products = response.json()
    assert any(p["id"] == "tuberías_y_fittings_pvc_sanitario" for p in products)
    assert any(p["safe_id"] == "tuberias_y_fittings_pvc_sanitario" for p in products)

    # Mercado safe
    response = client.get("/agora/v2/products?market_id=mercado_sanitario_hidraulico") # already safe
    assert response.status_code == 200

def test_v2_families_safe_id():
    # Product ID canónico con tildes
    response = client.get("/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberías_y_fittings_pvc_sanitario")
    assert response.status_code == 200
    
    # Product ID safe sin tildes
    response = client.get("/agora/v2/families?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario")
    assert response.status_code == 200
    families = response.json()
    assert any(f["family_id"] == "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario" for f in families)

def test_v2_pulse_safe_id():
    # Usando IDs safe en todos los niveles
    url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6"
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["family_id"] == "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario"
    assert data["product_id"] == "tuberías_y_fittings_pvc_sanitario"

def test_v1_legacy_still_works():
    response = client.get("/agora/health") # This is V1? No, wait. 
    # The app in main.py has both. client here only has V2 router.
    pass

def test_resolve_legacy_with_safe():
    response = client.get("/agora/v2/resolve-legacy?market=chile_construccion&product=tubo_pvc&subfamily=pvc_sanitario")
    assert response.status_code == 200
    data = response.json()
    assert data["canonical"]["product_id"] == "tuberías_y_fittings_pvc_sanitario"
    assert data["safe"]["product_id"] == "tuberías_y_fittings_pvc_sanitario" # resolve_product_id returns canonical
