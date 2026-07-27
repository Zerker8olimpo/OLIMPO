from unittest.mock import AsyncMock

from backend.OSEngine.scanners.api_fetcher import APIFetcher


def _client_returning(results):
    client = AsyncMock()
    client.get_indicators.return_value = results
    return client


def test_fetch_ok_when_all_indicators_available():
    client = _client_returning({
        "dolar": {"status": "ok", "valor": 950.0, "fecha": "2026-07-27", "variacion_6m": 0.04},
        "ipc": {"status": "ok", "valor": 0.3, "fecha": "2026-07-27", "variacion_6m": 0.02},
        "uf": {"status": "ok", "valor": 38000.0, "fecha": "2026-07-27", "variacion_6m": 0.01},
    })
    fetcher = APIFetcher(client=client)

    result = fetcher.fetch()

    assert result["source"] == "api"
    assert set(result["data"].keys()) == {"dolar", "ipc", "uf"}
    assert result["quality"]["status"] == "ok"
    assert result["quality"]["confidence"] == 0.9
    assert result["quality"]["errors"] == []


def test_fetch_partial_when_some_indicators_fail():
    client = _client_returning({
        "dolar": {"status": "ok", "valor": 950.0, "fecha": "2026-07-27", "variacion_6m": 0.04},
        "ipc": {"status": "error", "error": "timeout"},
        "uf": {"status": "error", "error": "timeout"},
    })
    fetcher = APIFetcher(client=client)

    result = fetcher.fetch()

    assert result["quality"]["status"] == "partial"
    assert result["quality"]["confidence"] == 0.4
    assert "ipc" in result["quality"]["missing_fields"]
    assert any("timeout" in e for e in result["quality"]["errors"])


def test_fetch_failed_when_no_indicators_available():
    client = _client_returning({
        "dolar": {"status": "error", "error": "timeout"},
        "ipc": {"status": "error", "error": "timeout"},
        "uf": {"status": "error", "error": "timeout"},
    })
    fetcher = APIFetcher(client=client)

    result = fetcher.fetch()

    assert result["data"] == {}
    assert result["quality"]["status"] == "failed"
    assert result["quality"]["confidence"] == 0.0
