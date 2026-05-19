
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
from sqlalchemy.exc import ProgrammingError
from datetime import datetime, timezone, timedelta

from backend.api.main import app
from backend.api.db_deps import get_db

client = TestClient(app)

@pytest.fixture
def admin_token():
    token = "test-admin-token"
    with patch.dict(os.environ, {"AGORA_ADMIN_TOKEN": token}):
        yield token

def test_meli_status_no_table_resilience(admin_token):
    """
    TAREA 6: Verificar que /meli/status no explote si la tabla no existe.
    """
    mock_db = MagicMock()
    # Simulamos que inspector no encuentra la tabla
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["users"] # No esta agora_metadata
    
    with patch("backend.api.routers.agora_admin.inspect", return_value=mock_inspector):
        app.dependency_overrides[get_db] = lambda: mock_db
        response = client.get(
            "/agora/v2/admin/meli/status",
            headers={"X-AGORA-ADMIN-TOKEN": admin_token}
        )
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata_error"] == "agora_metadata table not available"
        assert data["token_source"] in ["none", "env"]

def test_agora_metadata_service_rollback():
    """
    TAREA 5: Verificar que el servicio hace rollback ante error de DB.
    """
    from backend.agora.agora_metadata_service import AgoraMetadataService
    mock_db = MagicMock()
    mock_db.query.side_effect = ProgrammingError("SELECT...", params={}, orig=Exception("Table missing"))
    
    # get
    res = AgoraMetadataService.get(mock_db, "key")
    assert res is None
    assert mock_db.rollback.called

    # set
    mock_db.rollback.reset_mock()
    AgoraMetadataService.set(mock_db, "key", "val")
    assert mock_db.rollback.called

def test_script_create_agora_metadata_exists():
    """
    TAREA 3: Verificar existencia del script.
    """
    assert os.path.exists("backend/scripts/create_agora_metadata.py")

def test_observe_family_auth_error_reporting(admin_token):
    """
    TAREA 7: Verificar reporte de error de auth en observe-family.
    """
    from backend.agora.price_intelligence.price_observer import PriceObserver
    
    # El mock de search_items ahora debe devolver el diccionario estructurado
    with patch("backend.agora.price_intelligence.price_observer.MercadoLibreClient.search_items") as mock_search:
        mock_search.return_value = {
            "status": "forbidden",
            "http_status": 403,
            "raw_count_api": 0,
            "items": [],
            "error": "Mercado Libre rejected search request (Forbidden)"
        }
        
        # Mock de OAuth para evitar que intente consultar DB o que devuelva valores seguros
        mock_oauth = MagicMock()
        mock_oauth.get_valid_access_token = AsyncMock(return_value="fake-token")
        
        with patch("backend.agora.price_intelligence.price_observer.MeliOAuthClient", return_value=mock_oauth):
            app.dependency_overrides[get_db] = lambda: MagicMock()
            response = client.post(
                "/agora/v2/admin/observe-family",
                headers={"X-AGORA-ADMIN-TOKEN": admin_token},
                json={
                    "market_id": "mercado_sanitario_hidraulico", 
                    "product_id": "tuberias_y_fittings_pvc_sanitario", 
                    "family_id": "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario"
                }
            )
            app.dependency_overrides.clear()
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["source_status"] == "forbidden"
            assert data["data_status"] == "source_error"
            assert "source_requests" in data
            assert len(data["source_requests"]) > 0
            assert data["source_requests"][0]["http_status"] == 403
