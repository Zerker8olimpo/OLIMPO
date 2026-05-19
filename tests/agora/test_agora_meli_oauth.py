
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone, timedelta

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

def test_meli_oauth_callback_persisted(meli_creds, client_with_db, db_session):
    """
    Verifica que el callback persiste el token y responde con 'persisted': true.
    """
    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "valid-token", 
                "refresh_token": "refresh-123",
                "expires_in": 3600,
                "user_id": 123
            }
        )
        
        response = client_with_db.get("/agora/v2/admin/meli/oauth/callback?code=test_code")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["persisted"] is True
        assert data["token_source"] == "db"
        
        # Verificar en DB
        from backend.agora.agora_metadata_service import AgoraMetadataService
        meta = AgoraMetadataService.get(db_session, "meli_access_token")
        assert meta.value == "valid-token"
        assert meta.expires_at is not None

@pytest.mark.anyio
async def test_meli_token_lifecycle_async(db_session):
    """
    Verifica que el servicio maneja la comparacion naive vs aware sin error.
    """
    from backend.agora.price_intelligence.source_clients.meli_oauth import MeliOAuthClient
    from backend.agora.agora_metadata_service import AgoraMetadataService
    
    client_meli = MeliOAuthClient()
    
    # 1. Aware datetime en DB
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    AgoraMetadataService.set(db_session, "meli_access_token", "token-aware", expires_at=future)
    
    token = await client_meli.get_valid_access_token(db_session)
    assert token == "token-aware"
    
    # 2. Naive datetime en DB (simulando lo que podria pasar en algunos motores o migraciones)
    # Usamos un offset muy grande (24h) para evitar que el shift de zona horaria lo expire de inmediato
    naive_future = datetime.now() + timedelta(hours=24)
    AgoraMetadataService.set(db_session, "meli_access_token", "token-naive", expires_at=naive_future)
    
    token = await client_meli.get_valid_access_token(db_session)
    assert token == "token-naive"

def test_meli_oauth_callback_error(meli_creds, client_with_db):
    with patch("backend.agora.price_intelligence.source_clients.meli_oauth.MeliOAuthClient.exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = {"error": "invalid_grant", "error_description": "Code expired"}
        
        response = client_with_db.get("/agora/v2/admin/meli/oauth/callback?code=expired_code")
        
        assert response.status_code == 200 # Ahora responde 200 con ok: False
        data = response.json()
        assert data["ok"] is False
        assert "Code expired" in data["error"]
