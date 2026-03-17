from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.core.plans import PLANS, PLAN_MODEL_MAP
from backend.database.models.user import User
from backend.services.subscription_service import get_active_subscription

router = APIRouter(
    prefix="/bootstrap",
    tags=["bootstrap"],
)


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


@router.get("/")
async def bootstrap(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims),
):
    claims = claims or {}

    raw_user_id = claims.get("user_id")
    device_id = claims.get("device_id")

    resolved_user_id = _coerce_int(raw_user_id)
    resolved_device_id = _coerce_str(device_id)

    user: User | None = None

    if resolved_user_id is not None:
        user = db.query(User).filter(User.id == resolved_user_id).first()

    if user is None:
        return {
            "user": None,
            "subscription": {
                "active": False,
                "plan": None,
                "status": "inactive",
                "expires_at": None,
            },
            "limits": {
                "max_runs_per_day": 0,
                "max_horizon": 0,
            },
        }

    user_device_id = _coerce_str(getattr(user, "device_id", None))

    if user_device_id and resolved_device_id and user_device_id != resolved_device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DEVICE_MISMATCH",
        )

    user_id = _coerce_int(getattr(user, "id", None))
    user_email = _coerce_str(getattr(user, "email", None))
    user_full_name = _coerce_str(getattr(user, "full_name", None))

    active_sub = get_active_subscription(db, user_id=user.id) if user_id is not None else None

    plan_id = _coerce_str(getattr(active_sub, "plan_id", None)) if active_sub else None
    effective_plan = plan_id or "basic"

    plan_cfg = PLANS.get(effective_plan, PLANS.get("basic", {}))
    limits_cfg = plan_cfg.get("limits", {})
    models_enabled = PLAN_MODEL_MAP.get(effective_plan, [])

    display_name = user_full_name or (
        user_email.split("@")[0] if user_email and "@" in user_email else user_email
    )

    return {
        "user": {
            "id": str(user_id) if user_id is not None else None,
            "email": user_email,
            "display_name": display_name,
        },
        "subscription": {
            "active": bool(active_sub),
            "plan": active_sub.plan_id if active_sub else None,
            "status": "active" if active_sub else "inactive",
            "expires_at": active_sub.end_date.isoformat() if active_sub and active_sub.end_date else None,
        },
        "limits": {
            "max_runs_per_day": int(limits_cfg.get("max_runs_per_day", 0) or 0),
            "max_horizon": int(limits_cfg.get("max_horizon", 0) or 0),
        },
    }
