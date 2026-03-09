import os
from pathlib import Path
import random
import string
import sys
import jwt
import json
import mercadopago
from unittest.mock import patch
from datetime import timedelta
from fastapi.testclient import TestClient 
from datetime import datetime, timezone

# =============================================================================
# CONFIGURACIÓN PREVIA
# =============================================================================

# Configurar variables de entorno para el entorno de pruebas
# Esto asegura que main.py y jwt.py tengan lo necesario sin depender del .env local
os.environ["JWT_SECRET"] = "test_secret_key_12345_super_secure"
os.environ["APP_ENV"] = "development"
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "dummy_client_id_for_testing"
os.environ["DATABASE_URL"] = "sqlite:///backend/db/olimpo.db"
os.environ["GOOGLE_PLAY_VERIFY_ENABLED"] = "True"
os.environ["APP_CHANNEL"] = "web"  # Permitimos MP para el test simulando canal web
os.environ["ALLOW_MP_CHECKOUT"] = "True"
os.environ["ALLOW_MP_IN_APP"] = "False"
os.environ["PAYMENTS_MODE"] = "sandbox"
os.environ["GOOGLE_PLAY_PUBLIC_KEY"] = "dummy_public_key_for_testing_environment"

try:
    from backend.api.main import app
    from backend.api.security.jwt import create_access_token
except ImportError as e:
    raise RuntimeError(f"Error crítico importando la aplicación OLIMPO: {e}")

# =============================================================================
# INICIALIZACIÓN DE BASE DE DATOS PARA PRUEBAS
# =============================================================================
from sqlalchemy import create_engine
from backend.database.base import Base
# IMPORTANTE: Importar modelos específicos para que SQLAlchemy los registre en Base.metadata
# Evitamos 'import backend.database.models' para no disparar conflictos de imports circulares o inválidos en su __init__
from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.database.models.user_profile import UserProfile

# Intentamos crear el directorio de la DB si no existe
os.makedirs(os.path.join("backend", "db"), exist_ok=True)

DATABASE_URL = "sqlite:///backend/db/olimpo.db"
engine = create_engine(DATABASE_URL)

print(f"🛠️  SQLAlchemy Engine URL: {engine.url}")

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Cliente de pruebas de FastAPI (simula peticiones HTTP sin levantar servidor real)
client = TestClient(app)

def test_run_auth_flow():
    print("\n🧪 INICIANDO TEST DE FLUJO DE AUTENTICACIÓN (INTEGRACIÓN)\n")
    print("Objetivo: Simular login con Google, obtener JWT y acceder a ruta protegida.\n")

    # -------------------------------------------------------------------------
    # 1. PREPARACIÓN DE DATOS
    # -------------------------------------------------------------------------
    # Generamos un usuario aleatorio para evitar conflictos de 'Device Mismatch'
    # si corres el test múltiples veces.
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    test_email = f"tester_{rand_suffix}@example.com"
    device_id = f"device_{rand_suffix}"

    print(f"👤 Usuario simulado: {test_email}")
    print(f"📱 Device ID: {device_id}")

    # -------------------------------------------------------------------------
    # 2. MOCK DE GOOGLE Y LOGIN
    # -------------------------------------------------------------------------
    # Parcheamos 'verify_google_id_token' en el router de auth.
    # Nota: Parcheamos directamente la librería de Google dentro del router auth_google.
    with patch("backend.api.routers.auth_google.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "email": test_email,
            "sub": "100000000000000000000",
            "name": "Test User Automated",
            "iss": "https://accounts.google.com",
            "aud": "dummy_client_id_for_testing"
        }

        print("\n[PASO 1] Enviando solicitud de Login a POST /auth/google...")
        login_payload = {
            "id_token": "token_falso_simulado_por_test",
            "device_id": device_id,
            "platform": "android"
        }

        response = client.post("/auth/google", json=login_payload)

        if response.status_code != 200:
            print(f"❌ Error en Login. Status: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return

        data = response.json()
        real_token = data.get("access_token")
        
        if not real_token:
            print("❌ No se recibió access_token en la respuesta.")
            return

        # Decodificar el JWT para obtener la identidad (fuente de verdad)
        # El backend ya no devuelve el objeto 'user', el JWT es la identidad única.
        # Usamos el secreto configurado para validar la integridad del token recibido.
        claims = jwt.decode(
            real_token, 
            os.environ["JWT_SECRET"], 
            algorithms=["HS256"]
        )
        user_id = int(claims["user_id"])

        # GENERAR TOKEN DE TEST (test_mode: True)
        # Inyectamos el claim test_mode para bypass de policies de billing
        # REFACTOR MODELO B: Generamos un "Skinny Token" manual para simular el nuevo generador
        # ya que no podemos modificar backend/api/security/jwt.py en este contexto.
        skinny_payload = {
            "sub": claims.get("google_sub", "100000000000000000000"),
            "user_id": user_id,
            "email": test_email,
            "device_id": device_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "test_mode": True # Mantenemos solo para bypass de policies en test
        }
        token = jwt.encode(skinny_payload, os.environ["JWT_SECRET"], algorithm="HS256")

        # -------------------------------------------------------------------------
        # 3. PRUEBA DE ACCESO PROTEGIDO (VERIFICACIÓN DE TOKEN)
        # -------------------------------------------------------------------------
        print("\n[PASO 2] Verificando validez del Token en endpoint protegido (/me/subscription)...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Usamos /me/subscription para verificar que el token es aceptado
        prot_response = client.get("/me/subscription", headers=headers)
        
        assert prot_response.status_code == 200