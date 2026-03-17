import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.security.deps import get_current_claims
from backend.api.db_deps import get_db
from backend.services.subscription_service import get_active_subscription

router = APIRouter(prefix="/account", tags=["account"])
logger = logging.getLogger(__name__)


def format_subscription_status(sub):
    return {
        "active": bool(sub),
        "plan": sub.plan_id if sub else None,
        "status": "active" if sub else "inactive",
        "expires_at": sub.end_date.isoformat() if sub and sub.end_date else None,
    }


@router.get("/subscription")
def get_account_subscription(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    user_id = claims.get("user_id")
    if not user_id:
        return format_subscription_status(None)

    user_id = int(user_id)
    sub = get_active_subscription(db, user_id=user_id)

    response = format_subscription_status(sub)
    logger.info(
        f"[ACCOUNT] plan={response['plan']} active={response['active']}"
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
    return get_account_subscription(claims, db)