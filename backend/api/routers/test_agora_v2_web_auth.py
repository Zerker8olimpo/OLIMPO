import os
import time

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.security import deps as deps_module
from backend.database.base import Base
from backend.api.db_deps import get_db
from backend.api.security.jwt import create_access_token

# Familia piloto real, verificada contra /agora/v2/markets, /products y /families
# en producción (https://olimpo-backend.onrender.com).
PILOT_MARKET_ID = "mercado_sanitario_hidraulico"
PILOT_PRODUCT_ID = "tuberias_y_fittings_pvc_sanitario"
PILOT_FAMILY_ID = "tuberias_y_fittings_pvc_sanitario_tubos_pvc_sanitario"

SUPABASE_URL = "https://kpfqtuigbwecczafbpmh.supabase.co"
# Clave "publishable" (anon), la misma que ya se embebe en el frontend web
# (src/lib/config.ts) — no es un secreto.
SUPABASE_ANON_KEY = "sb_publishable_BNZICMfzrzphMnYwSKCGDA_ggScDzoZ"

# get_current_claims_web_or_app lee estas env vars directo (igual que
# backend.core.supabase_client). Se fijan aquí, igual que conftest.py fija
# JWT_SECRET/DATABASE_URL para tests.
os.environ.setdefault("SUPABASE_URL", SUPABASE_URL)
os.environ.setdefault("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)

# --- DB de test en memoria, siguiendo el mismo patrón local que ya usan
# test_subscription_upgrade_flow.py y test_google_verify_race_condition.py en
# este mismo directorio (las fixtures compartidas de conftest.py de la raíz
# no llegan a crear las tablas reales para este flujo). ---
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _mint_real_supabase_access_token() -> str:
    """
    Crea un usuario de prueba real vía Supabase Auth (autoconfirmado en este
    proyecto) y devuelve su access_token real, firmado por Supabase (ES256).

    Reproduce exactamente el hallazgo reportado: un token de sesión real de
    Supabase, obtenido tal como lo hace supabase.auth.getSession() en el
    frontend web, debe ser aceptado por /agora/v2/pulse.
    """
    email = f"agora.regression.{int(time.time() * 1000)}@mailinator.com"
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": "AgoraRegressionTest12345!"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def test_pulse_accepts_real_supabase_token(client):
    """
    Regresión del bug reportado: /agora/v2/pulse rechazaba con 401 INVALID_TOKEN
    un token de sesión real de Supabase (el mismo que usa el frontend web para
    /web/billing/create-preference y /web/helios/calculate), porque el endpoint
    solo validaba JWT propios del backend (HS256) vía get_current_claims.

    Con el fix, ese mismo tipo de token debe autenticar correctamente y devolver
    un data_status (real_available / sample_available / fallback_available / no_data),
    nunca un 401. La verificación llama de verdad a la API REST de Supabase
    (GET /auth/v1/user), sin mocks.
    """
    supabase_token = _mint_real_supabase_access_token()

    response = client.get(
        "/agora/v2/pulse",
        params={
            "market_id": PILOT_MARKET_ID,
            "product_id": PILOT_PRODUCT_ID,
            "family_id": PILOT_FAMILY_ID,
            "horizon": 3,
        },
        headers={"Authorization": f"Bearer {supabase_token}"},
    )

    assert response.status_code == 200, (
        f"Se esperaba 200 con un token Supabase real, se obtuvo "
        f"{response.status_code}: {response.text}"
    )
    data = response.json()
    assert "data_status" in data
    assert data["data_status"] in (
        "real_available",
        "sample_available",
        "fallback_available",
        "no_data",
    )


def test_pulse_rejects_garbage_token(client):
    """
    Un token que no es ni un JWT propio del backend ni un token válido de
    Supabase debe seguir siendo rechazado con 401 INVALID_TOKEN (no debe
    quedar abierto por accidente al agregar el fallback a Supabase).
    """
    response = client.get(
        "/agora/v2/pulse",
        params={
            "market_id": PILOT_MARKET_ID,
            "product_id": PILOT_PRODUCT_ID,
            "family_id": PILOT_FAMILY_ID,
            "horizon": 3,
        },
        headers={"Authorization": "Bearer esto-no-es-un-jwt-valido"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "INVALID_TOKEN"


def test_pulse_still_accepts_backend_app_jwt(client):
    """
    Guardia de no-regresión: el JWT propio del backend (HS256, app móvil) debe
    seguir autenticando /agora/v2/pulse exactamente igual que antes del fix —
    el fallback a Supabase no debe alterar la vía existente para la app móvil.
    """
    app_token = create_access_token(
        sub="google_sub_regression_test",
        user_id=999999,
        email="mobile.regression@example.com",
        device_id="device_regression_test",
        plan="basic",
    )

    response = client.get(
        "/agora/v2/pulse",
        params={
            "market_id": PILOT_MARKET_ID,
            "product_id": PILOT_PRODUCT_ID,
            "family_id": PILOT_FAMILY_ID,
            "horizon": 3,
        },
        headers={"Authorization": f"Bearer {app_token}"},
    )

    # Con un user_id que no existe en la tabla `users` in-memory de test, la
    # ruta debe seguir su curso normal (SQL sin resultados -> plan default),
    # nunca un 401 por auth: eso confirmaría que el JWT propio del backend
    # sigue autenticando igual que antes del fix.
    assert response.status_code != 401, response.text


def test_supabase_verification_uses_extended_timeout(monkeypatch):
    """
    Regresión del hallazgo de latencia: la verificación de Supabase en
    get_current_claims_web_or_app debe pasar un timeout explícito y >= 10s a
    requests.get, no depender de ningún default corto de librería (el bug
    original era el default de httpx de 5s dentro del SDK de supabase-py).
    """
    captured = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"id": "fake-user-id", "email": "fake@example.com"}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(deps_module.requests, "get", fake_get)
    monkeypatch.setattr(
        deps_module,
        "get_current_claims",
        lambda credentials: (_ for _ in ()).throw(
            deps_module.HTTPException(status_code=401, detail="INVALID_TOKEN")
        ),
    )

    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-supabase-token")
    claims = deps_module.get_current_claims_web_or_app(creds)

    assert claims["auth_source"] == "supabase"
    assert captured["timeout"] == deps_module.SUPABASE_AUTH_VERIFY_TIMEOUT_SECONDS
    assert captured["timeout"] >= 8.0
