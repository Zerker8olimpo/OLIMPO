# backend/api/routers/me.py
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.core.plans import PLAN_MODEL_MAP


router = APIRouter(prefix="/me", tags=["me"])


@router.get("/subscription")
def me_subscription(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """
    Usa JWT OLIMPO. claims["email"] identifica el usuario.
    Respuesta estable para Flutter.
    """
    email = claims.get("email")
    device_id = claims.get("device_id")
    if not email:
        return {"active": False, "plan": "basic", "plan_id": "basic", "models": [], "expires_at": None}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"active": False, "plan": "basic", "plan_id": "basic", "models": [], "expires_at": None}

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.device_id == device_id,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    is_active = False
    plan_id = "basic"
    
    expires_at = None

    if sub and sub.status == "active" and sub.end_date and sub.end_date > datetime.utcnow():
        is_active = True
        plan_id = sub.plan_id
        expires_at = sub.end_date.isoformat()

    models = PLAN_MODEL_MAP.get(plan_id, [])

    return {
        "active": is_active,
        "has_active_plan": is_active,
        "plan": plan_id,
        "plan_id": plan_id,
        "models": models,
        "models_enabled": models,
        "expires_at": expires_at
    }
