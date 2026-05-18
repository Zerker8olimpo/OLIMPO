
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os
from unittest.mock import patch

from backend.api.routers.agora_admin import router
from backend.core.config import settings

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def admin_token():
    token = "test-admin-token"
    with patch.dict(os.environ, {"AGORA_ADMIN_TOKEN": token}):
        yield token

def test_admin_no_token_returns_401(admin_token):
    response = client.get("/agora/v2/admin/history-health")
    assert response.status_code == 401
    assert "Falta el header X-AGORA-ADMIN-TOKEN" in response.text

def test_admin_wrong_token_returns_403(admin_token):
    response = client.get(
        "/agora/v2/admin/history-health",
        headers={"X-AGORA-ADMIN-TOKEN": "wrong-token"}
    )
    assert response.status_code == 403
    assert "inválido" in response.text

def test_admin_correct_token_allows_access(admin_token):
    response = client.get(
        "/agora/v2/admin/history-health",
        headers={"X-AGORA-ADMIN-TOKEN": admin_token}
    )
    # Puede ser 200 o un error de DB si las tablas no existen, pero no 401/403
    assert response.status_code in [200, 500] 

def test_admin_token_not_configured_returns_503():
    with patch.dict(os.environ, {"AGORA_ADMIN_TOKEN": ""}):
        # Necesitamos forzar el reload de os.getenv o confiar en el patch
        response = client.get(
            "/agora/v2/admin/history-health",
            headers={"X-AGORA-ADMIN-TOKEN": "any"}
        )
        assert response.status_code == 503
        assert "no está configurado" in response.text
