# backend/api/routers/me.py
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.core.plans import PLAN_MODEL_MAP
from backend.api.routers.account import format_subscription_status


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

    return format_subscription_status(sub)
