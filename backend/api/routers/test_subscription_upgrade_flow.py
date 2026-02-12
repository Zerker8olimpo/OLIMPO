import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ajusta los imports según la estructura de tu proyecto
from backend.api.main import app
from backend.database.base import Base
from backend.database.models.subscription import Subscription, PaymentProvider
from backend.database.models.user import User
from backend.api.db_deps import get_db
from backend.api.security.jwt import create_access_token
from backend.api.routers import billing_google

# --- CONFIGURACIÓN DE BASE DE DATOS DE TEST (SQLite en memoria) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture para la sesión de DB
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

# Fixture para el cliente de FastAPI con override de dependencia
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- MOCK DE GOOGLE PLAY ---
def fake_google_validation_pro(product_id, token):
    future_date = datetime.utcnow() + timedelta(days=30)
    return {
        "expiryTimeMillis": int(future_date.timestamp() * 1000),
        "autoRenewing": True,
        "startTimeMillis": int(datetime.utcnow().timestamp() * 1000)
    }

def test_upgrade_basic_to_pro(client, db_session, monkeypatch):
    """
    Valida el flujo de upgrade de plan:
    1. Usuario tiene plan Basic activo.
    2. Compra plan Pro en Google Play.
    3. Backend actualiza la suscripción existente (UPDATE) en lugar de crear una nueva.
    """

    # 1️⃣ Crear Usuario y Suscripción Basic inicial
    user = User(email="upgrade_test@example.com", device_id="device_upgrade_123", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    BASIC_TOKEN = "basic_token_123"
    PRO_TOKEN = "pro_token_456"

    basic_sub = Subscription(
        user_id=user.id,
        device_id=user.device_id,
        plan_id="basic",
        status="active",
        external_ref=BASIC_TOKEN,
        start_date=datetime.utcnow() - timedelta(days=5),
        end_date=datetime.utcnow() + timedelta(days=25),
        auto_renew=True,
        provider=PaymentProvider.GOOGLE,
    )
    db_session.add(basic_sub)
    db_session.commit()

    # Generar JWT válido para el usuario
    jwt_token = create_access_token(
        sub="google_sub_upgrade",
        user_id=user.id,
        email=user.email,
        device_id=user.device_id,
        plan="basic"
    )

    # 2️⃣ Mockear Google validation
    monkeypatch.setattr(
        billing_google, "verify_with_google_play", fake_google_validation_pro
    )

    # 3️⃣ Ejecutar upgrade a Pro
    response = client.post(
        "/billing/google/verify",
        json={
            "product_id": "olimpo_pro_monthly",
            "purchase_token": PRO_TOKEN,
        },
        headers={"Authorization": f"Bearer {jwt_token}"}
    )

    assert response.status_code == 200, f"Error en request: {response.text}"
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["subscription"]["plan"] == "pro"

    # 4️⃣ Verificar actualización en DB
    # Refrescamos la sesión para asegurar datos frescos
    db_session.expire_all()
    
    subs = db_session.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.device_id == user.device_id
    ).all()

    # Confirmar que solo existe UNA suscripción (UPDATE, no INSERT)
    assert len(subs) == 1, f"Se encontraron {len(subs)} suscripciones, se esperaba 1 (Upgrade in-place)."
    
    sub = subs[0]
    assert sub.plan_id == "pro"
    assert sub.status == "active"
    assert sub.external_ref == PRO_TOKEN
    assert sub.end_date > datetime.utcnow()
    assert sub.provider == PaymentProvider.GOOGLE