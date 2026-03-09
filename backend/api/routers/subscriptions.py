# backend/api/routers/subscriptions.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.api.schemas.subscription import SubscriptionStatusResponse
from backend.services.subscription_service import get_active_subscription, get_entitlements_for_plan

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/status", response_model=SubscriptionStatusResponse)
def subscription_status(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    user_id = int(claims["user_id"])
    device_id = claims.get("device_id")

    sub = get_active_subscription(db, user_id=user_id, device_id=device_id)
    if not sub:
        return SubscriptionStatusResponse(planId=None, status="no_plan", entitlements=[])

    return SubscriptionStatusResponse(
        planId=sub.plan_id,
        status="active",
        entitlements=get_entitlements_for_plan(sub.plan_id),
    )