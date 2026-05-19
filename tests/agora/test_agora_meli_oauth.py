
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os

from backend.api.main import app

client = TestClient(app)

@pytest.fixture
def admin_token():
    token = "test-admin-token"
    with patch.dict(os.environ, {"AGORA_ADMIN_TOKEN": token}):
        yield token

@pytest.fixture
def meli_creds():
    with patch.dict(os.environ, {
        "MELI_CLIENT_ID": "123",
        "MELI_CLIENT_SECRET": "secret",
        "MELI_REDIRECT_URI": "http://localhost/callback"
    }):
        yield

def test_meli_oauth_url_requires_token(admin_token):
    response = client.get("/agora/v2/admin/meli/oauth/url")
    assert response.status_code == 401

def test_meli_oauth_url_success(admin_token, meli_creds):
    response = client.get(
        "/agora/v2/admin/meli/oauth/url",
        headers={"X-AGORA-ADMIN-TOKEN": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "auth.mercadolibre.cl" in data["authorization_url"]
    assert "client_id=123" in data["authorization_url"]

def test_meli_status(admin_token, meli_creds):
    response = client.get(
        "/agora/v2/admin/meli/status",
        headers={"X-AGORA-ADMIN-TOKEN": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True

def test_meli_oauth_callback_liberado(meli_creds):
    """
    Verifica que el callback NO requiere token (está liberado para redirección).
    """
    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.MeliOAuthClient.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"access_token": "abc", "user_id": 123}
        
        # Llamada SIN header de admin token
        response = client.get("/agora/v2/admin/meli/oauth/callback?code=test_code&state=my_state")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["state"] == "my_state"

def test_meli_oauth_callback_error(meli_creds):
    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.MeliOAuthClient.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"error": "invalid_grant", "error_description": "Code expired"}
        
        response = client.get("/agora/v2/admin/meli/oauth/callback?code=expired_code")
        
        assert response.status_code == 400
        assert "Error en OAuth de Mercado Libre" in response.json()["detail"]
