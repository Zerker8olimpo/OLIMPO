import logging
import requests
from typing import Literal
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from backend.core.settings import settings
from backend.services.credit_service import add_credits, supabase as sb_admin

logger = logging.getLogger("olimpo.billing")
router = APIRouter(prefix="/web/billing", tags=["web-billing"])

PLAN_CONFIG = {
    "starter": {"credits": 30, "price_usd": 5, "price_clp": 4900},
    "pro": {"credits": 120, "price_usd": 15, "price_clp": 14500},
    "business": {"credits": 250, "price_usd": 25, "price_clp": 24000},
}


class CreatePreferenceRequest(BaseModel):
    plan: Literal["starter", "pro", "business"]


def _get_user_id(authorization: str) -> str:
    from backend.core.supabase_client import supabase as sb_client
    token = authorization.replace("Bearer ", "")
    user_response = sb_client.auth.get_user(token)
    return user_response.user.id


@router.get("/plans")
def get_plans():
    return PLAN_CONFIG


@router.post("/create-preference")
def create_preference(
    payload: CreatePreferenceRequest,
    authorization: str = Header(...),
):
    if not settings.ALLOW_MP_CHECKOUT:
        raise HTTPException(status_code=403, detail="MERCADOPAGO_CHECKOUT_DISABLED")

    try:
        user_id = _get_user_id(authorization)
    except Exception as e:
        logger.error(f"Token Supabase inválido: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")

    plan = PLAN_CONFIG[payload.plan]

    body = {
        "items": [{
            "title": f"Olimpo {payload.plan.upper()} — {plan['credits']} créditos",
            "quantity": 1,
            "unit_price": plan["price_clp"],
            "currency_id": "CLP",
        }],
        "external_reference": f"{user_id}:{payload.plan}",
        "notification_url": f"{settings.PUBLIC_BASE_URL}/web/billing/webhook/mercadopago",
        "back_urls": {
            "success": f"{settings.PUBLIC_BASE_URL}/billing?payment=success",
            "failure": f"{settings.PUBLIC_BASE_URL}/billing?payment=failure",
            "pending": f"{settings.PUBLIC_BASE_URL}/billing?payment=pending",
        },
        "auto_return": "approved",
    }

    resp = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        json=body,
        headers={
            "Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    if resp.status_code >= 400:
        logger.error(f"Error MercadoPago: {resp.text}")
        raise HTTPException(status_code=502, detail="No se pudo crear la preferencia de pago")

    data = resp.json()
    checkout_url = data.get("sandbox_init_point") if settings.PAYMENTS_MODE != "prod" else data.get("init_point")

    return {
        "checkout_url": checkout_url,
        "price_usd": plan["price_usd"],
        "price_clp": plan["price_clp"],
    }


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request):
    if not settings.MP_WEBHOOK_ENABLED:
        return {"ok": False}

    payload = await request.json()
    if payload.get("type") != "payment":
        return {"ok": True, "ignored": True}

    payment_id = str((payload.get("data") or {}).get("id", ""))
    if not payment_id:
        return {"ok": True, "ignored": True}

    resp = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}"},
    )
    if resp.status_code != 200:
        logger.error(f"No se pudo consultar el pago {payment_id}: {resp.text}")
        return {"ok": False}

    payment = resp.json()
    if payment.get("status") != "approved":
        return {"ok": True, "status": payment.get("status")}

    external_ref = payment.get("external_reference", "")
    if ":" not in external_ref:
        logger.error(f"external_reference inválido: {external_ref}")
        return {"ok": False}

    user_id, plan_id = external_ref.split(":", 1)
    plan = PLAN_CONFIG.get(plan_id)
    if not plan:
        logger.error(f"Plan desconocido en webhook: {plan_id}")
        return {"ok": False}

    existing = sb_admin.table("credit_purchases").select("mp_payment_id").eq("mp_payment_id", payment_id).execute()
    if existing.data:
        return {"ok": True, "already_processed": True}

    await add_credits(user_id, plan["credits"], plan_id)

    sb_admin.table("credit_purchases").insert({
        "mp_payment_id": payment_id,
        "user_id": user_id,
        "plan": plan_id,
        "credits": plan["credits"],
        "amount_clp": plan["price_clp"],
        "status": "approved",
    }).execute()

    return {"ok": True}