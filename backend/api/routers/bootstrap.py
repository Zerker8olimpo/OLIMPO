from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.core.plans import PLANS, PLAN_MODEL_MAP
from backend.database.models.subscription import Subscription
from backend.database.models.user import User

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


def _normalize_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


@router.get("/")
async def bootstrap(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims),
):
    claims = claims or {}

    raw_user_id = (
        request.headers.get("X-User-Id")
        or request.query_params.get("user_id")
        or claims.get("user_id")
    )

    device_id = (
        request.headers.get("X-Device-ID")
        or request.query_params.get("device_id")
        or claims.get("device_id")
    )

    resolved_user_id = _coerce_int(raw_user_id)
    resolved_device_id = _coerce_str(device_id)

    user: User | None = None

    # Resolver usuario:
    # 1) por header/query/claims si viene identificador explícito
    # 2) si no viene, usar el primer usuario disponible (compatibilidad legacy)
    if resolved_user_id is not None:
        user = db.query(User).filter(User.id == resolved_user_id).first()

    if user is None and resolved_user_id is None:
        user = db.query(User).order_by(User.id.asc()).first()

    # Mantener contrato estable aunque no haya usuario
    if user is None:
        return {
            "user": None,
            "subscription": {
                "status": "inactive",
                "plan_id": None,
                "has_active_plan": False,
                "models_enabled": [],
            },
            "limits": {
                "max_runs_per_day": 0,
                "max_horizon": 0,
            },
        }

    user_device_id = _coerce_str(getattr(user, "device_id", None))

    # Validar mismatch de dispositivo si el cliente/tóken envía device_id
    if user_device_id and resolved_device_id and user_device_id != resolved_device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DEVICE_MISMATCH",
        )

    user_id = _coerce_int(getattr(user, "id", None))
    user_email = _coerce_str(getattr(user, "email", None))
    user_full_name = _coerce_str(getattr(user, "full_name", None))

    sub: Subscription | None = None
    if user_id is not None:
        sub = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.end_date.desc())
            .first()
        )

    active_sub: Subscription | None = None

    sub_status = _coerce_str(getattr(sub, "status", None))
    sub_end = _normalize_datetime(getattr(sub, "end_date", None))

    if sub and sub_status == "active" and sub_end:
        now = datetime.now(timezone.utc)
        if sub_end > now:
            active_sub = sub

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
            "status": _coerce_str(getattr(active_sub, "status", None)) if active_sub else "inactive",
            "plan_id": plan_id,
            "has_active_plan": bool(active_sub),
            "models_enabled": models_enabled,
        },
        "limits": {
            "max_runs_per_day": int(limits_cfg.get("max_runs_per_day", 0) or 0),
            "max_horizon": int(limits_cfg.get("max_horizon", 0) or 0),
        },
    }