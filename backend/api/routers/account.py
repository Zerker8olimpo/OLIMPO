import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.models.subscription import Subscription
from backend.database.models.user import User
from backend.api.security.deps import get_current_claims
from backend.api.db_deps import get_db
from backend.core.plans import PLAN_MODEL_MAP

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


def format_subscription_status(
    sub: Optional[Subscription],
) -> dict:
    """
    Fuente única de verdad del estado de suscripción.
    """
    has_active_plan = bool(
        sub
        and sub.status == "active"
        and sub.end_date
        and sub.end_date > datetime.utcnow()
    )
    plan_id = sub.plan_id if sub else "basic"
    
    status = {
        "has_active_plan": has_active_plan,
        "plan": plan_id,
        "models_enabled": PLAN_MODEL_MAP.get(plan_id, []),
        "expires_at": sub.end_date.isoformat() if sub and sub.end_date else None,
        "provider": str(sub.provider.value if hasattr(sub.provider, 'value') else sub.provider) if sub else None,
    }

    return status


@router.get("/subscription")
def get_account_subscription(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    email = claims.get("email")
    device_id = claims.get("device_id")

    if not email or not device_id:
        return format_subscription_status(None)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return format_subscription_status(None)

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.device_id == device_id,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    response = format_subscription_status(sub)
    logger.info(
        f"[ACCOUNT] plan={response['plan']} active={response['has_active_plan']}"
    )
    return response


@router.get("/me")
def get_account_me(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    return get_account_subscription(claims, db)


@router.get("/status")
def get_account_status(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """
    Alias de compatibilidad para frontend antiguo.
    """
    return get_account_subscription(claims, db)