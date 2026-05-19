
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
import backend.database.models # Asegurar registro
from backend.api.main import app
from backend.api.db_deps import get_db

client = TestClient(app)

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def client_with_db(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield client
    app.dependency_overrides.clear()

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

def test_meli_status(admin_token, meli_creds, client_with_db):
    response = client_with_db.get(
        "/agora/v2/admin/meli/status",
        headers={"X-AGORA-ADMIN-TOKEN": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True

def test_meli_oauth_callback_liberado(meli_creds, client_with_db, db_session):
    """
    Verifica que el callback NO requiere token (está liberado para redirección)
    y persiste el token en la DB.
    """
    # Para que el mock persista en la DB, debemos programar el efecto secundario
    from backend.agora.agora_metadata_service import AgoraMetadataService
    
    async def side_effect(db, code):
        token_data = {"access_token": "abc-token", "user_id": 123, "expires_in": 3600}
        # Simulamos la persistencia que haría el cliente real
        from datetime import datetime, timezone, timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
        AgoraMetadataService.set(db, "meli_access_token", "abc-token", expires_at=expires_at)
        return token_data

    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.MeliOAuthClient.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.side_effect = side_effect
        
        response = client_with_db.get("/agora/v2/admin/meli/oauth/callback?code=test_code&state=my_state")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verificar persistencia en DB usando el servicio
        meta = AgoraMetadataService.get(db_session, "meli_access_token")
        assert meta is not None
        assert meta.value == "abc-token"

def test_meli_oauth_callback_error(meli_creds, client_with_db):
    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.MeliOAuthClient.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"error": "invalid_grant", "error_description": "Code expired"}
        
        response = client_with_db.get("/agora/v2/admin/meli/oauth/callback?code=expired_code")
        
        assert response.status_code == 400
        assert "Error en OAuth de Mercado Libre" in response.json()["detail"]
