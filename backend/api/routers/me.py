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
    if not email:
        return {"authenticated": False, "plan": "none", "provider": None, "status": "expired", "expires_at": None}

    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        return {"authenticated": True, "plan": "none", "provider": None, "status": "expired", "expires_at": None}

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).one_or_none()
    if not sub:
        return {"authenticated": True, "plan": "none", "provider": None, "status": "expired", "expires_at": None}

    expires_at = sub.end_date.isoformat() if sub.end_date else None
    # Si ya expiró y sigue "active", lo normalizas
    if sub.end_date and sub.status == "active":
        if sub.end_date < datetime.utcnow():
            sub.status = "expired"
            db.commit()

    return {
        "authenticated": True,
        "plan": sub.plan,
        "provider": sub.provider,
        "status": sub.status,
        "expires_at": expires_at
    }
