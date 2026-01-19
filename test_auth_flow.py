import os
import sys
import random
import string
import jwt
from unittest.mock import patch
from fastapi.testclient import TestClient

# =============================================================================
# CONFIGURACIÓN PREVIA
# =============================================================================

# Asegurar que el directorio raíz está en el path para importar backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar variables de entorno para el entorno de pruebas
# Esto asegura que main.py y jwt.py tengan lo necesario sin depender del .env local
os.environ["JWT_SECRET"] = "test_secret_key_12345_super_secure"
os.environ["APP_ENV"] = "development"
os.environ["GOOGLE_CLIENT_ID"] = "dummy_client_id_for_testing"

try:
    from backend.api.main import app
except ImportError as e:
    print("❌ Error crítico importando la aplicación.")
    print("Asegúrate de ejecutar este script desde la raíz del proyecto (carpeta OLIMPO).")
    print(f"Detalle del error: {e}")
    sys.exit(1)

# =============================================================================
# INICIALIZACIÓN DE BASE DE DATOS PARA PRUEBAS
# =============================================================================
from sqlalchemy import create_engine
from backend.database.base import Base

# Intentamos crear el directorio de la DB si no existe
os.makedirs(os.path.join("backend", "db"), exist_ok=True)

engine = create_engine("sqlite:///backend/db/olimpo.db")
Base.metadata.create_all(bind=engine)

# Cliente de pruebas de FastAPI (simula peticiones HTTP sin levantar servidor real)
client = TestClient(app)

def run_auth_test():
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
    # Esto evita llamar a Google real y nos permite inyectar datos de usuario exitosos.
    with patch("backend.api.routers.auth.verify_google_id_token") as mock_verify:
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
        token = data.get("access_token")
        
        if not token:
            print("❌ No se recibió access_token en la respuesta.")
            return

        print(f"✅ Login Exitoso.")
        print(f"🔑 JWT Recibido: {token[:25]}... (truncado)")

        # -------------------------------------------------------------------------
        # NUEVO: VERIFICACIÓN DE CONTENIDO DEL JWT (PLAN Y MODELOS)
        # -------------------------------------------------------------------------
        try:
            # Decodificamos el token para inspeccionar los claims
            # Usamos el mismo secreto y algoritmo que el backend
            decoded_payload = jwt.decode(
                token, 
                os.environ["JWT_SECRET"], 
                algorithms=["HS256"]
            )
            print(f"📋 Claims del JWT: {decoded_payload}")

            # Verificación de identidad
            if decoded_payload.get("email") == test_email:
                print("✅ JWT de identidad verificado correctamente.")
                print("ℹ️  Nota: El plan y modelos se resuelven dinámicamente en el servidor (Arquitectura Fase 1).")

        except Exception as e:
            print(f"❌ Error decodificando el JWT: {e}")

        # -------------------------------------------------------------------------
        # NUEVO: PRUEBA DE RESTRICCIÓN DE PLAN (403 FORBIDDEN)
        # -------------------------------------------------------------------------
        print("\n[PASO 1.1] Probando restricción de plan (Acceso a SIGMA sin plan)...")
        
        sigma_response = client.post(
            "/sigma/run",
            json={"data": "test_payload"},
            headers={"Authorization": f"Bearer {token}"}
        )

        if sigma_response.status_code == 403:
            print("✅ ÉXITO: El acceso fue denegado correctamente (403 Forbidden).")
            print(f"📦 Detalle del servidor: {sigma_response.json()['detail']['message']}")
        else:
            print(f"❌ FALLÓ: Se esperaba 403, pero se obtuvo {sigma_response.status_code}")

        # -------------------------------------------------------------------------
        # 3. PRUEBA DE ACCESO PROTEGIDO
        # -------------------------------------------------------------------------
        # Usamos el token obtenido para llamar a un endpoint que requiere autenticación.
        # Usaremos /billing/google/verify como ejemplo de ruta protegida.
        print("\n[PASO 2] Probando acceso a ruta protegida POST /billing/google/verify...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Payload válido para activar el stub en development
        verify_payload = {
            "purchase_token": "test_purchase_token_123",
            "product_id": "olimpo_pro_monthly"
        }

        prot_response = client.post(
            "/billing/google/verify",
            json=verify_payload,
            headers=headers
        )

        # -------------------------------------------------------------------------
        # 4. VERIFICACIÓN DE RESULTADOS
        # -------------------------------------------------------------------------
        if prot_response.status_code == 401:
            print("❌ FALLÓ: El token fue rechazado (401 Unauthorized).")
            print("   Esto indica que el middleware o la dependencia de seguridad no validó el JWT.")
        
        elif prot_response.status_code == 200:
            print("✅ ÉXITO: El endpoint protegido aceptó el token.")
            print(f"📦 Respuesta del servidor: {prot_response.json()}")
            print("\n🎉 El flujo de autenticación funciona correctamente de punta a punta.")
        
        else:
            # Si da otro error (ej: 500, 400), al menos sabemos que pasó la auth (no fue 401)
            print(f"⚠️  El token fue aceptado (Auth OK), pero el endpoint respondió: {prot_response.status_code}")
            print(f"Respuesta: {prot_response.text}")

if __name__ == "__main__":
    run_auth_test()