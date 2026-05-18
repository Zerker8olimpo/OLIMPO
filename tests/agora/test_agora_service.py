import pytest
from backend.agora.agora_service import AgoraService

@pytest.mark.anyio
async def test_agora_pulse_pvc_sanitario():
    service = AgoraService()
    response = await service.get_pulse(
        market="chile_construccion",
        product="tubo_pvc",
        subfamily="pvc_sanitario",
        horizon=6,
        unit_cost=3100,
        user_price=4300
    )
    
    assert response.market == "chile_construccion"
    assert response.product == "tubo_pvc"
    assert response.subfamily == "pvc_sanitario"
    assert response.observation.current_reference_price == 4390
    assert response.projection.horizon_months == 6
    assert response.margin_reference.enabled is True
    assert response.margin_reference.unit_cost == 3100
    assert response.margin_reference.user_current_margin_percent is not None
    assert response.commercial_interpretation.suggested_signal == "revisar_precio_con_cautela"

@pytest.mark.anyio
async def test_agora_pulse_horizons():
    service = AgoraService()
    for h in [3, 6, 12]:
        response = await service.get_pulse(
            market="chile_construccion",
            product="tubo_pvc",
            subfamily="pvc_sanitario",
            horizon=h
        )
        assert response.projection.horizon_months == h
        assert response.projection.base > 0

@pytest.mark.anyio
async def test_agora_pulse_no_margin_without_cost():
    service = AgoraService()
    response = await service.get_pulse(
        market="chile_construccion",
        product="tubo_pvc",
        subfamily="pvc_sanitario",
        horizon=6
    )
    assert response.margin_reference.enabled is False
    assert response.margin_reference.unit_cost is None

def test_agora_get_markets():
    service = AgoraService()
    markets = service.get_markets()
    assert len(markets) > 0
    assert markets[0]["id"] == "chile_construccion"

def test_agora_get_products():
    service = AgoraService()
    products = service.get_products("chile_construccion")
    assert len(products) > 0
    assert products[0]["id"] == "tubo_pvc"

def test_agora_get_subfamilies():
    service = AgoraService()
    subfamilies = service.get_subfamilies("tubo_pvc")
    assert len(subfamilies) >= 2
    ids = [s["id"] for s in subfamilies]
    assert "pvc_sanitario" in ids
    assert "pvc_hidraulico" in ids
