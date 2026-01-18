# backend/api/routers/billing_mercadopago.py
from datetime import datetime, timedelta

import os
import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.database.models.payment import Payment
# from backend.core.email_service import send_subscription_active_email # Uncomment if available


router = APIRouter(prefix="/billing/mercadopago", tags=["billing-mercadopago"])

MP_API = "https://api.mercadopago.com"
MP_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")


class MPCreateRequest(BaseModel):
    plan: str  # basic | pro | enterprise
    period: str = "monthly"


@router.post("/create")
def mp_create(
    payload: MPCreateRequest,
    claims: dict = Depends(get_current_claims),
):
    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADOPAGO_ACCESS_TOKEN_NOT_SET")

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_CLAIMS")

    prices = {"basic": 19990, "pro": 29990, "enterprise": 39990}
    if payload.plan not in prices:
        raise HTTPException(status_code=400, detail="INVALID_PLAN")

    # En tu web, debes loguear con el mismo JWT OLIMPO y llamar este endpoint.
    # external_reference = email (o user_id). Aquí uso email para evitar dependencia.
    preference_payload = {
        "items": [{
            "title": f"OLIMPO {payload.plan.upper()} {payload.period}",
            "quantity": 1,
            "currency_id": "CLP",
            "unit_price": prices[payload.plan]
        }],
        "external_reference": email,
        # "notification_url": "https://TU_RENDER_URL/billing/mercadopago/webhook",
    }

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(f"{MP_API}/checkout/preferences", json=preference_payload, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()

    return {
        "preference_id": data["id"],
        "checkout_url": data.get("init_point") or data.get("sandbox_init_point")
    }


@router.post("/webhook")
async def mp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str | None = Header(default=None),
):
    # Firma controlada (placeholder). En producción se implementa firma real según docs MP.
    if MP_WEBHOOK_SECRET and x_signature != MP_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_SIGNATURE")

    payload = await request.json()

    # En eventos reales, suele venir payment_id y hay que consultar el pago.
    # Para tenerlo operativo hoy, soportamos payloads con:
    # { "status": "approved", "external_reference": "<email>", "plan": "pro", "payment_id": "..." }
    status = payload.get("status")
    external_reference = payload.get("external_reference")
    plan = payload.get("plan")
    payment_id = payload.get("payment_id")

    if not external_reference:
        raise HTTPException(status_code=400, detail="MISSING_EXTERNAL_REFERENCE")

    if status != "approved":
        return {"ok": True}

    if plan not in ("basic", "pro", "enterprise"):
        # Si no envías plan en webhook, deberás obtenerlo consultando el pago en MP.
        raise HTTPException(status_code=400, detail="MISSING_OR_INVALID_PLAN")

    user = db.query(User).filter(User.email == external_reference).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    start = datetime.utcnow()
    end = start + timedelta(days=30)

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).one_or_none()
    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan=plan,
            status="active",
            provider="mercadopago",
            external_reference=str(payment_id) if payment_id else None,
            start_date=start,
            end_date=end,
            auto_renew=True,
        )
        db.add(sub)
    else:
        sub.plan = plan
        sub.status = "active"
        sub.provider = "mercadopago"
        sub.external_reference = str(payment_id) if payment_id else None
        sub.start_date = start
        sub.end_date = end
        sub.auto_renew = True

    db.add(Payment(
        user_id=user.id,
        provider="mercadopago",
        amount=0,
        currency="CLP",
        status="approved",
        external_id=str(payment_id) if payment_id else None,
    ))

    db.commit()
    return {"ok": True}