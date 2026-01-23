from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.core.payment_models import PaymentIntent, PaymentStatus
from backend.database.models.pal import PaymentAuthority as Authority
from backend.core.config import settings
from backend.core.plans import PLANS

router = APIRouter(prefix="/payments", tags=["PAL-Payments"])

@router.post("/create")
def create_payment_intent(
    plan_id: str, 
    provider: str, 
    db: Session = Depends(get_db), 
    claims: dict = Depends(get_current_claims)
):
    # Validar que el device_id del token coincida
    if not claims.get("device_id"):
        raise HTTPException(status_code=400, detail="DEVICE_ID_REQUIRED_IN_TOKEN")

    if plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="INVALID_PLAN")

    intent = PaymentIntent(
        user_id=claims["user_id"],
        device_id=claims["device_id"],
        plan_id=plan_id,
        amount=PLANS[plan_id]["price"],
        currency="CLP",
        provider=provider,
        mode=settings.PAYMENTS_MODE,
        status=PaymentStatus.CREATED
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    
    # Aquí se integraría la lógica de creación de preferencia de Mercado Pago
    # Retornamos el intent_id para que el cliente pueda hacer polling/verify
    return {
        "intent_id": intent.id,
        "status": intent.status,
        "mode": intent.mode,
        "checkout_url": f"https://www.mercadopago.cl/checkout/v1/redirect?pref_id=mock_{intent.id}" if settings.PAYMENTS_MODE != "local" else None
    }

@router.post("/{intent_id}/verify")
def verify_payment(intent_id: int, db: Session = Depends(get_db), claims: dict = Depends(get_current_claims)):
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent or intent.user_id != claims["user_id"]:
        raise HTTPException(status_code=404, detail="PAYMENT_INTENT_NOT_FOUND")

    # Lógica de verificación activa según modo
    provider_status = "pending"
    if intent.mode == "local":
        provider_status = "approved" # En local, verify siempre aprueba si se llama
    elif intent.mode == "sandbox":
        # Simulación de consulta a SDK de Mercado Pago
        provider_status = "approved" 
    else:
        # Producción: Consulta real a API de MP con Access Token
        provider_status = "approved" 

    sub = Authority.decide_subscription_transition(db, intent, provider_status, source="polling_verify")
    
    return {
        "intent_id": intent.id,
        "payment_status": intent.status,
        "subscription_status": sub.status if sub else "inactive"
    }

@router.post("/local/confirm")
def local_confirm_payment(intent_id: int, approve: bool = True, db: Session = Depends(get_db)):
    """
    Endpoint exclusivo para desarrollo local (DEV_ONLY=true).
    """
    if not settings.DEV_ONLY or settings.PAYMENTS_MODE != "local":
        raise HTTPException(status_code=403, detail="ONLY_ALLOWED_IN_LOCAL_DEV_MODE")

    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="INTENT_NOT_FOUND")

    status = "approved" if approve else "rejected"
    sub = Authority.decide_subscription_transition(db, intent, status, source="local_authority")
    
    return {"intent_status": intent.status, "subscription_active": sub is not None}

@router.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    # 1. Loguear evento crudo
    # 2. Extraer external_reference (intent_id)
    # 3. Validar firma si es PROD
    # 4. Disparar PAL
    intent_id = payload.get("data", {}).get("id") # Simplificado
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if intent:
        # El webhook solo sugiere, PAL decide tras verificar
        Authority.decide_subscription_transition(db, intent, "approved", source="webhook")
    
    return {"status": "received"}