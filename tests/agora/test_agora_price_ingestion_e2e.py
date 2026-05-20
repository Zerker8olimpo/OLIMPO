
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import io
from unittest.mock import patch

from backend.database.base import Base
import backend.database.models # Asegura registro de modelos
from backend.api.main import app
from backend.api.db_deps import get_db

from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_session():
    # check_same_thread=False + StaticPool es necesario para SQLite in-memory 
    # compartido entre hilos/conexiones del mismo engine
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Asegurar registro de modelos ÁGORA
    import backend.database.models
    
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

from backend.api.security.deps import get_current_claims

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_claims] = lambda: {"user_id": "1", "plan": "enterprise"}
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token():
    token = "e2e-token"
    with patch.dict(os.environ, {"AGORA_ADMIN_TOKEN": token}):
        yield token

def test_agora_price_ingestion_and_snapshot_e2e(client, admin_token):
    headers = {"X-AGORA-ADMIN-TOKEN": admin_token}
    
    # 1. Verificar salud inicial
    resp = client.get("/agora/v2/admin/history-health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True, f"Health check failed: {data.get('error')}"
    assert data["observations_count"] == 0
    
    # 2. Importar CSV
    csv_content = (
        "market_id,product_id,family_id,source,source_type,raw_product_name,normalized_product_name,price,currency,observed_at,confidence\n"
        "mercado_sanitario_hidraulico,tuberias_y_fittings_pvc_sanitario,tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario,test_source,manual,Tubo Test,tubo,5000,CLP,2026-05-18,1.0\n"
        "mercado_sanitario_hidraulico,tuberias_y_fittings_pvc_sanitario,tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario,test_source,manual,Tubo Test 2,tubo,6000,CLP,2026-05-19,1.0\n"
        "mercado_sanitario_hidraulico,tuberias_y_fittings_pvc_sanitario,tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario,test_source,manual,Tubo Test 3,tubo,5500,CLP,2026-05-20,1.0\n"
    )
    
    file = ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    resp = client.post(
        "/agora/v2/admin/price-observations/import-csv",
        headers=headers,
        files={"file": file}
    )
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 3
    
    # 3. Construir Snapshot
    build_req = {
        "market_id": "mercado_sanitario_hidraulico",
        "product_id": "tuberias_y_fittings_pvc_sanitario",
        "family_id": "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario",
        "month": "2026-05"
    }
    resp = client.post("/agora/v2/admin/snapshots/build", headers=headers, json=build_req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["sample_size"] == 3
    assert data["data_status"] == "real_available"
    
    # 4. Validar Pulse (Debe usar datos reales ahora)
    pulse_url = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario&horizon=6"
    resp = client.get(pulse_url)
    assert resp.status_code == 200
    pulse = resp.json()
    
    assert pulse["observation"]["current_reference_price"] == 5500 # Mediana de 5000, 5500, 6000
    assert pulse["data_status"] == "real_available"
    assert len(pulse["history_series"]) > 0
    assert pulse["source_context"]["real_web_observation"] is True # Marcado como real
    
    # 5. Validar familia sin datos (No debe inventar 4390)
    # tuberias_y_fittings_pvc_sanitario_codos_pvc_sanitario existe en catálogo pero no le cargamos datos en este test
    pulse_url_empty = "/agora/v2/pulse?market_id=mercado_sanitario_hidraulico&product_id=tuberias_y_fittings_pvc_sanitario&family_id=tuberias_y_fittings_pvc_sanitario_codos_pvc_sanitario&horizon=6"
    resp = client.get(pulse_url_empty)
    assert resp.status_code == 200
    pulse_empty = resp.json()
    assert pulse_empty["observation"]["current_reference_price"] is None
    assert pulse_empty["data_status"] == "no_data"
    assert pulse_empty["history_series"] == []
