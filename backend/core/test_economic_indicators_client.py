import pytest
from unittest.mock import patch, MagicMock

from backend.core.economic_indicators_client import EconomicIndicatorsClient


def _mock_response(payload):
    return MagicMock(json=lambda: payload, raise_for_status=lambda: None)


@pytest.mark.anyio
async def test_get_indicator_ok_computes_variacion_6m():
    serie = [{"fecha": "2026-07-01", "valor": 110.0}] + [{"fecha": "x", "valor": 100.0}] * 5
    with patch("backend.core.economic_indicators_client.httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response({"serie": serie})
        client = EconomicIndicatorsClient()
        result = await client.get_indicator("dolar")

    assert result["status"] == "ok"
    assert result["valor"] == 110.0
    assert result["variacion_6m"] == pytest.approx(0.10)


@pytest.mark.anyio
async def test_get_indicator_ipc_compounds_monthly_rates_instead_of_pct_of_pct():
    # mindicador.cl "ipc" ya es una tasa mensual (%), no un índice de nivel.
    # variacion_6m debe componer las tasas, no aplicar (actual-pasado)/pasado.
    serie = [{"fecha": "x", "valor": v} for v in [0.3, -0.2, 0.4, 0.0, 0.9, -0.4, 0.2]]
    with patch("backend.core.economic_indicators_client.httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response({"serie": serie})
        client = EconomicIndicatorsClient()
        result = await client.get_indicator("ipc")

    expected = 1.0
    for v in [0.3, -0.2, 0.4, 0.0, 0.9, -0.4]:
        expected *= (1 + v / 100.0)
    expected -= 1

    assert result["variacion_6m"] == pytest.approx(expected)


@pytest.mark.anyio
async def test_get_indicator_network_error_returns_error_status():
    with patch("backend.core.economic_indicators_client.httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("connection refused")
        client = EconomicIndicatorsClient()
        result = await client.get_indicator("dolar")

    assert result["status"] == "error"
    assert result["valor"] is None
    assert "connection refused" in result["error"]


@pytest.mark.anyio
async def test_get_indicator_uses_cache_within_ttl():
    with patch("backend.core.economic_indicators_client.httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response({"serie": [{"fecha": "x", "valor": 900.0}]})
        client = EconomicIndicatorsClient(cache_ttl_seconds=3600)

        await client.get_indicator("uf")
        await client.get_indicator("uf")

    assert mock_get.call_count == 1


@pytest.mark.anyio
async def test_get_indicators_fetches_multiple_codes():
    with patch("backend.core.economic_indicators_client.httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = _mock_response({"serie": [{"fecha": "x", "valor": 50.0}]})
        client = EconomicIndicatorsClient()
        results = await client.get_indicators(["dolar", "ipc"])

    assert set(results.keys()) == {"dolar", "ipc"}
    assert results["dolar"]["status"] == "ok"
    assert results["ipc"]["status"] == "ok"
