from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.services.subscription_service import get_active_subscription

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/subscription")
def me_subscription(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
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
