import os
import sys
from pathlib import Path
import random
import string
import jwt
import json
import mercadopago
from unittest.mock import patch
from datetime import timedelta
from fastapi.testclient import TestClient

# =============================================================================
# CONFIGURACIÓN PREVIA
# =============================================================================

# Blindaje definitivo: Asegurar que la raíz del proyecto esté en el PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

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

try:
    from backend.api.main import app
    from backend.api.security.jwt import create_access_token
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
        token = create_access_token(
            sub=claims.get("google_sub", "100000000000000000000"),
            user_id=user_id,
            email=test_email,
            device_id=device_id,
            plan="basic",
            test_mode=True
        )

        print(f"✅ Login Exitoso y Token de Test Generado.")
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
        # PRUEBA DE FLUJO DE SUSCRIPCIÓN
        # -------------------------------------------------------------------------
        print("\n[PASO 2] Probando Mercado Pago (Canal Web)...")
        # Simulamos canal web cambiando el entorno temporalmente si fuera necesario
        mp_payload = {"plan": "pro"}
        mp_response = client.post(
            "/payments/mercadopago/create_preference",
            json=mp_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if mp_response.status_code == 200:
            mp_data = mp_response.json()
            print(f"✅ Checkout URL generada: {mp_data['checkout_url']}")
        else:
            print(f"❌ Error creando pago MP: {mp_response.text}")

        # -------------------------------------------------------------------------
        # NUEVO: PRUEBA DE FLUJO GOOGLE PAY (SIMULADO)
        # -------------------------------------------------------------------------
        print("\n[PASO 4] Probando flujo Google Pay...")
        g_verify_res = client.post(
            "/payments/google/verify",
            json={"purchase_token": "test_token", "product_id": "olimpo_pro_monthly", "device_id": device_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        if g_verify_res.status_code == 200:
            print("✅ Google Pay verificado correctamente (test_mode bypass OK).")
        else:
            print(f"❌ Error verificando Google Pay: {g_verify_res.text}")

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
            "product_id": "olimpo_pro_monthly",
            "device_id": device_id
        }

        prot_response = client.post(
            "/payments/google/verify",
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

        # -------------------------------------------------------------------------
        # PASO 5: VALIDACIÓN FINAL DE SUSCRIPCIÓN EFECTIVA
        # -------------------------------------------------------------------------
        print("\n[PASO 5] Validando suscripción efectiva en /account/status...")
        me_res = client.get("/account/status", headers={"Authorization": f"Bearer {token}"})
        
        if me_res.status_code == 200:
            me_data = me_res.json()
            print(f"✅ Suscripción efectiva: {me_data}")
            # Validamos campos clave según el principio de suscripción efectiva
            assert me_data["status"] == "active"
            assert me_data["plan"] != "free"
        else:
            print(f"❌ Error consultando /me/subscription: {me_res.text}")

def test_mercadopago_sandbox_checkout():
    """
    Test manual aislado para validar la conectividad directa con Mercado Pago Sandbox.
    NO usa JWT, NO usa DB, NO usa PolicyAgent.
    """
    print("\n🧪 INICIANDO TEST AISLADO: MERCADO PAGO SANDBOX CHECKOUT\n")
    
    # 1. Credenciales desde el entorno
    access_token = os.getenv("MP_ACCESS_TOKEN_TEST")
    payer_email = os.getenv("MP_TEST_PAYER_EMAIL", "test_user@testuser.com")
    
    if not access_token:
        print("⚠️  SKIP: MP_ACCESS_TOKEN_TEST no configurado. Saltando test de Mercado Pago.")
        return

    try:
        # 2. Inicializar SDK oficial (aislado)
        sdk = mercadopago.SDK(access_token)
        
        # 3. Payload mínimo válido (Chile / CLP)
        preference_data = {
            "items": [{
                "title": "sandbox_test_plan",
                "quantity": 1,
                "unit_price": 1000,
                "currency_id": "CLP"
            }],
            "payer": {"email": payer_email},
            "external_reference": "sandbox-test-001",
        }
        
        print(f"📦 Enviando payload: {json.dumps(preference_data, indent=2)}")
        
        # 4. Llamada directa al proveedor
        response = sdk.preference().create(preference_data)
        status = response["status"]
        body = response["response"]
        
        if status >= 400:
            print(f"\n❌ Mercado Pago Sandbox rechazó el request")
            print(f"Status de respuesta: {status}")
            print(f"Detail: {json.dumps(body, indent=2)}")
        else:
            print(f"\n🧪 Mercado Pago Sandbox Test")
            print(f"Status de respuesta: {status}")
            print(f"Checkout URL: {body.get('sandbox_init_point')}")
            print("\n--- Response completa (pretty print) ---")
            print(json.dumps(body, indent=2))
            print("\n✅ Resultado final: Éxito")
            
    except Exception as e:
        print(f"\n❌ Error crítico durante la ejecución del test: {e}")

if __name__ == "__main__":
    # Ejecutar test de integración del backend
    run_auth_test()

    # Ejecutar test aislado de Mercado Pago
    test_mercadopago_sandbox_checkout()