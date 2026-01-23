# backend/api/routers/me.py
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User
from backend.database.models.subscription import Subscription


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
        return {"authenticated": False, "plan": "basic", "provider": None, "status": "inactive", "expires_at": None}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"authenticated": True, "plan": "basic", "provider": None, "status": "inactive", "expires_at": None}

    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.device_id == device_id,
            Subscription.status == "active",
            Subscription.end_date > datetime.utcnow()
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    if not sub:
        return {"authenticated": True, "plan": "basic", "provider": None, "status": "inactive", "expires_at": None}

    return {
        "authenticated": True,
        "plan": sub.plan_id,
        "provider": sub.provider,
        "status": sub.status,
        "expires_at": sub.end_date.isoformat() if sub.end_date else None
    }
