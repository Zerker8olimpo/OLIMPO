import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from backend.api.main import app
from backend.api.routers import bootstrap
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims

# Incluir el router manualmente para el test ya que no podemos editar main.py
app.include_router(bootstrap.router)

client = TestClient(app)

# --- MOCKS & FIXTURES ---

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_claims():
    return {
        "user_id": 100,
        "device_id": "device_test_100",
        "email": "test@example.com"
    }

def override_deps(db_mock, claims_mock):
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[get_current_claims] = lambda: claims_mock

def teardown_deps():
    app.dependency_overrides = {}

# --- TESTS ---

def test_bootstrap_active_plan(mock_db, mock_claims):
    """
    Valida que un usuario con plan activo reciba has_active_plan=True y los modelos correctos.
    """
    override_deps(mock_db, mock_claims)
    
    # Mock User
    user = User(id=100, email="test@example.com", device_id="device_test_100")
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Mock Active Subscription
    sub = Subscription(
        user_id=100,
        plan_id="pro",
        status="active",
        end_date=datetime.now(timezone.utc) + timedelta(days=10),
        provider="google_play"
    )
    # Mock get_active_subscription query chain
    # deps.py: db.query(Subscription).filter(...).order_by(...).first()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = sub

    response = client.get("/bootstrap")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["user"]["id"] == "100"
    assert data["subscription"]["has_active_plan"] is True
    assert data["subscription"]["plan_id"] == "pro"
    assert "epsilon" in data["subscription"]["models_enabled"] # Asumiendo PRO incluye epsilon
    assert data["limits"]["max_runs_per_day"] > 0

    teardown_deps()

def test_bootstrap_no_plan(mock_db, mock_claims):
    """
    Valida que un usuario sin suscripción reciba has_active_plan=False pero status 200.
    """
    override_deps(mock_db, mock_claims)
    
    user = User(id=100, email="test@example.com", device_id="device_test_100")
    mock_db.query.return_value.filter.return_value.first.return_value = user
    
    # Mock No Subscription (None)
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    response = client.get("/bootstrap")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["subscription"]["has_active_plan"] is False
    assert data["subscription"]["plan_id"] is None
    assert data["subscription"]["status"] == "inactive"
    # Debe devolver límites básicos (ej. 0 o default)
    assert "limits" in data

    teardown_deps()

def test_bootstrap_expired_plan(mock_db, mock_claims):
    """
    Valida que si la suscripción expiró (end_date < now), se trate como sin plan.
    La lógica de get_active_subscription en deps.py ya filtra por fecha.
    """
    override_deps(mock_db, mock_claims)
    
    user = User(id=100, email="test@example.com")