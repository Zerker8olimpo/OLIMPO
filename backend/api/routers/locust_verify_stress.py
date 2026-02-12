from locust import HttpUser, task, between, events
import os
import logging

# Configuración de logging para Locust
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token constante para probar idempotencia masiva
PURCHASE_TOKEN = "stress_test_token_100_concurrent"

# JWT de prueba (Debe ser válido en el entorno destino o mockeado)
# Se recomienda generar uno con larga duración o usar un usuario de test fijo
TEST_JWT = os.getenv("TEST_JWT", "TEST_VALID_JWT_PLACEHOLDER")

class VerifyUser(HttpUser):
    # Tiempo de espera entre tareas (simula comportamiento humano o ráfaga)
    # Para estrés puro, valores bajos son mejores.
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """
        Se ejecuta al iniciar cada usuario virtual.
        Aquí podríamos hacer login si fuera necesario dinámicamente.
        """
        self.jwt = TEST_JWT
        if self.jwt == "TEST_VALID_JWT_PLACEHOLDER":
            logger.warning("⚠️ Usando JWT placeholder. Asegúrate de configurar TEST_JWT env var.")

    @task
    def verify_subscription(self):
        """
        Tarea principal: Golpear el endpoint de verificación.
        """
        headers = {
            "Authorization": f"Bearer {self.jwt}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "product_id": "olimpo_pro_monthly",
            "purchase_token": PURCHASE_TOKEN
        }

        with self.client.post(
            "/api/v1/billing/google/verify",
            json=payload,
            headers=headers,
            name="verify_google_subscription",
            catch_response=True
        ) as response:
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "SUCCESS":
                    response.success()
                else:
                    response.failure(f"Logical failure: {data}")
            elif response.status_code == 401:
                response.failure("Unauthorized - Check JWT")
            else:
                # Cualquier otro código (500, 400, etc.) es fallo
                response.failure(f"Unexpected status {response.status_code}: {response.text}")