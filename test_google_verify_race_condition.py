import threading
import time
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ajusta los imports según la estructura de tu proyecto
from backend.api.main import app
from backend.database.base import Base
from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.api.db_deps import get_db
from backend.api.security.jwt import create_access_token
from backend.api.routers import billing_google

# --- CONFIGURACIÓN DE BASE DE DATOS DE TEST (SQLite en memoria) ---
# check_same_thread=False es CRÍTICO para tests con threading en SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture para la sesión de DB y el ciclo de vida de las tablas
@pytest.fixture(scope="function")
def testing_db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)

# Fixture para el cliente de FastAPI con override de dependencia
@pytest.fixture(scope="function")
def client(testing_db):
    def override_get_db():
        # Cada llamada al endpoint obtiene su propia sesión,
        # lo que es seguro para concurrencia.
        session = testing_db()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- MOCK DE GOOGLE PLAY ---
@pytest.fixture
def mock_google_validation(monkeypatch):
    def fake_validate(product_id, token):
        # Pequeño delay para aumentar la probabilidad de solapamiento en hilos
        time.sleep(0.05)
        return { 
            "expiryTimeMillis": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000),
            "autoRenewing": True,
            "startTimeMillis": int(datetime.now(timezone.utc).timestamp() * 1000)
        }
    
    # Mockeamos la función en el módulo donde se usa
    monkeypatch.setattr(billing_google, "verify_with_google_play", fake_validate)

# --- TEST DE RACE CONDITION ---
def test_verify_google_race_condition(client, testing_db, mock_google_validation):
    """
    Simula dos peticiones simultáneas al endpoint de verificación con el mismo token.
    Objetivo: Validar que el manejo de IntegrityError funciona y garantiza idempotencia.
    """
    
    # 1. Preparar Datos: Usuario y Token JWT
    db_session = testing_db()
    user = User(email="race_test@example.com", device_id="device_race_123", is_active=True)
    db_session.add(user)
    db_session.commit()
    # Refrescamos para asegurar que el ID está disponible y el objeto está atado a la sesión
    db_session.refresh(user)

    jwt_token = create_access_token(
        sub="google_sub_123",
        user_id=user.id,
        email=user.email,
        device_id=user.device_id,
        plan="basic"
    )
    # Cerramos la sesión explícitamente para asegurar que los datos están en la DB compartida (StaticPool)
    db_session.close()

    TEST_PURCHASE_TOKEN = "token_concurrente_unico_XYZ"
    PRODUCT_ID = "olimpo_pro_monthly"
    
    # Variable para capturar resultados de los hilos
    results = []
    errors = []

    def call_verify():
        try:
            response = client.post(
                "/billing/google/verify",
                json={
                    "product_id": PRODUCT_ID,
                    "purchase_token": TEST_PURCHASE_TOKEN,
                },
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            results.append(response)
        except Exception as e:
            errors.append(e)

    # 2. Ejecutar Hilos Simultáneos
    thread1 = threading.Thread(target=call_verify)
    thread2 = threading.Thread(target=call_verify)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # 3. Validaciones
    assert len(errors) == 0, f"Hubo excepciones en los hilos: {errors}"
    assert len(results) == 2, "No se completaron ambas peticiones"

    # Validación 1: Ambas respuestas deben ser exitosas (200 OK)
    # Una inserta, la otra recupera por idempotencia (o inserta si el lock lo permite secuencialmente)
    for res in results:
        assert res.status_code == 200, f"Falló una petición: {res.text}"
        assert res.json()["status"] == "SUCCESS"

    # Validación 2: Solo debe existir UNA fila en la base de datos
    subs = db_session.query(Subscription).filter(
        Subscription.external_ref == TEST_PURCHASE_TOKEN
    ).all()
    
    assert len(subs) == 1, f"Se esperaban 1 suscripción, se encontraron {len(subs)}. Falló el UNIQUE constraint o el manejo de concurrencia."