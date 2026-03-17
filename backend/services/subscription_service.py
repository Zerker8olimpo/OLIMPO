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
    """
    Fuente de verdad DB-first para suscripción activa.
    - status == "active"
    - end_date > now (o end_date NULL si decides permitirlo)
    """
    now = datetime.now(timezone.utc)

    q = db.query(Subscription).filter(
        Subscription.user_id == int(user_id),
        Subscription.status == "active",
        or_(Subscription.end_date.is_(None), Subscription.end_date > now),
    )

    subscription = q.order_by(Subscription.end_date.desc().nullslast()).first()

    return subscription


def resolve_plan(subscription: Optional[Subscription], claims: dict) -> Optional[str]:
    """
    Resuelve el plan del usuario. Prioriza la DB, pero usa el token como fallback.
    Es robusto contra MagicMock en tests.
    """
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
    """
    Deriva entitlements desde PLAN_MODEL_MAP (SSoT).
    plan_id: basic|pro|enterprise
    """
    models = PLAN_MODEL_MAP.get(plan_id, [])
    return [f"run_{m}" for m in models]


def get_user_plan(db: Session, user_id: int, claims: dict) -> str:
    """
    Obtiene el plan del usuario.
    1. Busca una suscripción activa en la base de datos.
    2. Si no existe, hace fallback al plan contenido en el token JWT.
    3. Si no hay nada, devuelve 'free' como plan base.
    """
    # 1. Buscar suscripción activa en DB
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).order_by(Subscription.end_date.desc()).first()

    # Si hay una suscripción activa en la DB, se usa ese plan.
    if sub:
        return sub.plan_id

    # 2. Fallback: Usar plan del JWT si existe
    return claims.get("plan", "free")


def check_entitlement(required_entitlement: str, plan: str) -> bool:
    """
    Verifica si un plan actual tiene el permiso requerido.
    """
    permissions = {
        "free": [],
        "basic": ["run_epsilon"],
        "pro": ["run_epsilon", "run_sigma", "run_poseidon"],
        "enterprise": ["run_epsilon", "run_sigma", "run_poseidon", "observatory"],
    }
    return required_entitlement in permissions.get(plan, [])