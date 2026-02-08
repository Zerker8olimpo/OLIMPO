import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.core.plans import PLAN_MODEL_MAP
from backend.database.models.user import User
from backend.database.models.payment import PaymentProvider
from backend.database.models.subscription import Subscription

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


@router.get("/subscription")
def get_account_subscription(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """
    Devuelve el estado REAL de la suscripción desde la base de datos.
    Fuente de verdad para el frontend.
    """
    email = claims.get("email")
    device_id = claims.get("device_id")
    
    default_response = {
        "active": False,
        "plan": "basic",
        "plan_id": "basic",
        "models": [],
        "expires_at": None
    }

    if not email:
        return default_response

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return default_response

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.device_id == device_id,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    plan_models = {
        "basic": ["epsilon"],
        "pro": ["epsilon", "sigma"],
        "enterprise": ["epsilon", "sigma", "poseidon"],
    }

    if sub and sub.status == "active" and sub.end_date and sub.end_date > datetime.utcnow():
        return {"active": True, "plan": sub.plan_id, "plan_id": sub.plan_id, "models": plan_models.get(sub.plan_id, []), "expires_at": sub.end_date.isoformat()}
    
    return default_response


@router.get("/me")
def get_account_me(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """
    Endpoint canónico de estado de cuenta.
    Fuente de verdad para el frontend sobre el plan y capacidades.
    """
    email = claims.get("email")
    device_id = claims.get("device_id")
    
    # Valores por defecto (Fallback)
    response = {
        "email": email,
        "plan": "basic",
        "has_active_plan": False,
        "subscription_provider": None,
        "models_enabled": PLAN_MODEL_MAP.get("basic", []),
    }

    if not email:
        return response

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return response

    # Consultar suscripción activa en DB
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.device_id == device_id,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    if sub and sub.status == "active" and sub.end_date and sub.end_date > datetime.utcnow():
        response["plan"] = sub.plan_id
        response["has_active_plan"] = True
        # Normalizamos el provider para el frontend
        provider_val = sub.provider.value if hasattr(sub.provider, 'value') else str(sub.provider)
        response["subscription_provider"] = "google_play" if "google" in str(provider_val).lower() else provider_val
        response["models_enabled"] = PLAN_MODEL_MAP.get(sub.plan_id, [])

    logger.info(f"[ACCOUNT] Returning plan={response['plan']} models={response['models_enabled']}")
    
    return response