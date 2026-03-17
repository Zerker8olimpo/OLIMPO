# backend/services/subscription_service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.core.plans import PLAN_MODEL_MAP
from backend.database.models.subscription import Subscription


def get_active_subscription(
    db: Session,
    user_id: int,
) -> Optional[Subscription]:
    now = datetime.now(timezone.utc)

    q = db.query(Subscription).filter(
        Subscription.user_id == int(user_id),
        Subscription.status == "active",
        or_(Subscription.end_date.is_(None), Subscription.end_date > now),
    )

    return q.order_by(Subscription.end_date.desc().nullslast()).first()


def resolve_plan(subscription: Optional[Subscription], claims: dict) -> Optional[str]:
    if subscription is not None:
        plan_id = getattr(subscription, "plan_id", None)
        if isinstance(plan_id, str) and plan_id.strip():
            return plan_id

    if isinstance(claims, dict):
        plan_from_claims = claims.get("plan")
        if isinstance(plan_from_claims, str) and plan_from_claims.strip():
            return plan_from_claims

    plan_from_claims = getattr(claims, "plan", None)
    if isinstance(plan_from_claims, str) and plan_from_claims.strip():
        return plan_from_claims

    return None


def get_entitlements_for_plan(plan_id: str) -> List[str]:
    models = PLAN_MODEL_MAP.get(plan_id, [])
    return [f"run_{m}" for m in models]


def get_user_plan(db: Session, user_id: int, claims: dict) -> str:
    sub = get_active_subscription(db, user_id=user_id)

    if sub and isinstance(sub.plan_id, str) and sub.plan_id.strip():
        return sub.plan_id

    if isinstance(claims, dict):
        token_plan = claims.get("plan")
        if isinstance(token_plan, str) and token_plan.strip():
            return token_plan

    return "free"


def check_entitlement(required_entitlement: str, plan: str) -> bool:
    permissions = {
        "free": [],
        "basic": ["run_epsilon"],
        "pro": ["run_epsilon", "run_sigma", "run_poseidon"],
        "enterprise": ["run_epsilon", "run_sigma", "run_poseidon", "observatory"],
    }
    return required_entitlement in permissions.get(plan, [])