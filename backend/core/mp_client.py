import os
import requests
from backend.core.settings import settings

class MercadoPagoClient:
    def __init__(self):
        self.enabled = os.getenv("ALLOW_MP_CHECKOUT", "false").lower() == "true"
        self.access_token = os.getenv("MP_ACCESS_TOKEN")

        if self.enabled and not self.access_token:
            raise RuntimeError(
                "Mercado Pago enabled but access token not configured."
            )

        self.base_url = "https://api.mercadopago.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def create_preference(self, intent_id: int, plan: str, amount: float, email: str):
        """Crea una preferencia de pago."""
        url = f"{self.base_url}/checkout/preferences"
        payload = {
            "items": [{
                "title": f"Plan OLIMPO: {plan.upper()}",
                "quantity": 1,
                "unit_price": amount,
                "currency_id": "CLP"
            }],
            "payer": {"email": email},
            "external_reference": str(intent_id),
            "notification_url": f"{settings.PUBLIC_BASE_URL}/payments/webhook",
            "back_urls": {
                "success": f"{settings.PUBLIC_BASE_URL}/payments/success",
                "failure": f"{settings.PUBLIC_BASE_URL}/payments/failure"
            },
            "auto_return": "approved"
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code >= 400:
            return None, response.text
            
        data = response.json()
        # En sandbox usamos sandbox_init_point
        checkout_url = data.get("sandbox_init_point") if settings.PAYMENTS_MODE != "prod" else data.get("init_point")
        return {
            "preference_id": data.get("id"),
            "checkout_url": checkout_url
        }, None

    def get_payment_by_intent(self, intent_id: int):
        """Busca el estado del pago usando la external_reference."""
        url = f"{self.base_url}/v1/payments/search"
        params = {"external_reference": str(intent_id)}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            return "pending"
            
        results = response.json().get("results", [])
        if not results:
            return "pending"
            
        # Retornamos el estado del pago más reciente
        # Estados MP: approved, rejected, pending, in_process, cancelled
        return results[0].get("status")