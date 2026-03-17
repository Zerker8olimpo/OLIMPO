from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.payments.models import PaymentIntent, PaymentStatus
from backend.payments.authority import Authority
from backend.core.config import settings
from backend.core.plans import PLANS

router = APIRouter(prefix="/payments", tags=["PAL-Payments"])

@router.post("/create")
def create_intent(plan_id: str, provider: str, db: Session = Depends(get_db), claims: dict = Depends(get_current_claims)):
    if plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="INVALID_PLAN")
    
    intent = PaymentIntent(
        user_id=claims["user_id"],
        device_id=claims["device_id"],
        plan_id=plan_id,
        amount=PLANS[plan_id]["price"],
        provider=provider,
        mode=settings.PAYMENTS_MODE,
        status=PaymentStatus.CREATED
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    
    # Si es modo local, el usuario debe llamar a /local/confirm para simular éxito
    return {"intent_id": intent.id, "status": intent.status, "mode": intent.mode}

@router.post("/{intent_id}/verify")
def verify_intent(intent_id: int, db: Session = Depends(get_db), claims: dict = Depends(get_current_claims)):
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent or intent.user_id != claims["user_id"]:
        raise HTTPException(status_code=404, detail="INTENT_NOT_FOUND")

    # Aquí se llamaría al provider real (MP/Google) para consultar estado actual
    # Por simplicidad en este bloque, simulamos que consultamos y obtenemos "approved"
    # En una implementación completa, aquí va el switch por provider.
    
    provider_status = "approved" # Mock de respuesta del proveedor
    sub = PaymentAuthority.decide_subscription_transition(db, intent, provider_status)
    
    return {"intent_status": intent.status, "subscription_active": sub is not None}

@router.post("/local/confirm")
def local_confirm(intent_id: int, approve: bool = True, db: Session = Depends(get_db)):
    """
    Endpoint exclusivo para desarrollo local.
    """
    if settings.PAYMENTS_MODE != "local":
        raise HTTPException(status_code=403, detail="ONLY_ALLOWED_IN_LOCAL_MODE")
    
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="INTENT_NOT_FOUND")
        
    status = "approved" if approve else "rejected"
    sub = PaymentAuthority.decide_subscription_transition(db, intent, status)
    
    return {"status": intent.status, "subscription_active": sub is not None}

@router.get("/me")
def get_my_subscription(
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims),
):
    from backend.services.subscription_service import get_active_subscription

    user_id = claims.get("user_id")
    if not user_id:
        return {"active": False, "plan": None, "status": "inactive", "expires_at": None}

    user_id = int(user_id)
    sub = get_active_subscription(db, user_id=user_id)

    return {
        "active": bool(sub),
        "plan": sub.plan_id if sub else None,
        "status": "active" if sub else "inactive",
        "expires_at": sub.end_date.isoformat() if sub and sub.end_date else None,
    }