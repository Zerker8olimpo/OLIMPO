from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.mp_client import MercadoPagoClient

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims, activate_subscription_logic
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment
from backend.core.plans import normalize_plan

router = APIRouter(tags=["Payments & Account"])

def get_mp_client() -> MercadoPagoClient:
    return MercadoPagoClient()

class GooglePayVerifyRequest(BaseModel):
    product_id: str
    purchase_token: str
    device_id: str

class MercadoPagoPreferenceRequest(BaseModel):
    plan: Literal["basic", "pro", "enterprise"]

# --- ENDPOINTS DE LA APP ---

# REMOVIDO: Endpoint stub de Google (/payments/google/verify). 
# La verificación real y canónica vive en backend/api/routers/billing_google.py

# --- ENDPOINTS WEB / EXTERNOS ---

@router.post("/payments/mercadopago/create_preference")
def create_mp_preference(
    payload: MercadoPagoPreferenceRequest,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    """
    Crea una preferencia de Mercado Pago (Solo para canal Web).
    IMPORTANT: Mercado Pago must NEVER be initiated from the Android app (Google Play policy).
    """
    # Auditoría de Seguridad: Rechazo explícito si el canal es Play Store o si se intenta forzar in-app
    if settings.APP_CHANNEL == "playstore" or settings.ALLOW_MP_IN_APP:
        raise HTTPException(
            status_code=403, 
            detail="Mercado Pago checkout is not available inside the app. Use external channel."
        )

    if not settings.ALLOW_MP_CHECKOUT:
        raise HTTPException(status_code=403, detail="MERCADOPAGO_CHECKOUT_DISABLED")

    plan_id = payload.plan
    amount = {"basic": 19990, "pro": 29990, "enterprise": 39990}.get(plan_id, 19990)
    user_id = int(claims["user_id"])
    device_id = claims.get("device_id")

    # Registrar pago localmente
    payment = Payment(
        user_id=user_id,
        provider="mercadopago",
        amount=amount,
        currency="CLP",
        status="created"
    )
    db.add(payment)
    db.commit()

    mp_client = get_mp_client()
    res, error = mp_client.create_preference(
        intent_id=payment.id,
        plan=plan_id,
        amount=amount,
        email=claims["email"]
    )

    if error:
        raise HTTPException(status_code=502, detail=f"Mercado Pago Error: {error}")

    payment.external_id = res["preference_id"]
    db.commit()

    return {"checkout_url": res["checkout_url"], "payment_id": payment.id}

# --- WEBHOOKS ---

@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(default=None),
):
    """
    Webhook para procesar pagos de Mercado Pago.
    IMPORTANT: Este flujo es exclusivamente para activaciones desde canales externos.
    """
    if not settings.MP_WEBHOOK_ENABLED:
        return {"ok": False, "detail": "WEBHOOK_DISABLED"}

    if settings.MP_WEBHOOK_SECRET and x_signature != settings.MP_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_SIGNATURE")

    payload = await request.json()
    # Lógica de procesamiento de MP...
    # (Se asume que activate_subscription_logic maneja la idempotencia)
    
    # Ejemplo simplificado de activación
    event_type = payload.get("type")
    payment_id = (payload.get("data") or {}).get("id")
    if event_type != "payment" or not payment_id:
        return {"ok": True, "ignored": True}
    
    return {"ok": True}