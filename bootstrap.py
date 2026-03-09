from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims, get_active_subscription
from backend.database.models.user import User
from backend.core.plans import PLANS, PLAN_MODEL_MAP

router = APIRouter()

# --- DTOs ---

class UserDTO(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None

class SubscriptionDTO(BaseModel):
    has_active_plan: bool
    plan_id: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    features: List[str]
    models_enabled: List[str]
    provider: Optional[str] = None

class LimitsDTO(BaseModel):
    max_runs_per_day: int
    max_horizon: int

class BootstrapResponse(BaseModel):
    user: UserDTO
    subscription: SubscriptionDTO
    limits: LimitsDTO

# --- ENDPOINT ---

@router.get("/bootstrap", response_model=BootstrapResponse)
def bootstrap_session(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    """
    Canonical source of truth for frontend session state.
    DB-First authority: Validates device lock and derives entitlements from DB.
    """
    user_id = int(claims["user_id"])
    token_device_id = claims["device_id"]

    # 1. Cargar Usuario y Validar Device Lock
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="USER_NOT_FOUND")

    # Regla de Negocio: 1 cuenta = 1 dispositivo activo.
    # Si el device_id en la DB (último login) no coincide con el del token,
    # significa que se inició sesión en otro lado.
    if user.device_id and user.device_id != token_device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DEVICE_MISMATCH"
        )

    # 2. Cargar Suscripción Activa (DB Authority)
    # get_active_subscription ya filtra por end_date > now() y status='active'
    sub = get_active_subscription(db, user_id)

    # 3. Derivar Estado
    if sub:
        plan_id = sub.plan_id
        sub_status = sub.status
        expires_at = sub.end_date
        provider = sub.provider
        has_active_plan = True
    else:
        # Fallback seguro: Sin plan activo
        plan_id = None
        sub_status = "inactive"
        expires_at = None
        provider = None
        has_active_plan = False

    # 4. Calcular Features y Límites (Desde Constantes, no JWT)
    # Si no hay plan, usamos 'basic' o 'free' como base para límites mínimos, o ceros.
    # Asumimos que PLANS tiene una key para el plan actual o fallback a 'basic'.
    effective_plan_id = plan_id if plan_id else "basic"
    plan_config = PLANS.get(effective_plan_id, PLANS.get("basic", {}))
    
    models_enabled = PLAN_MODEL_MAP.get(effective_plan_id, [])
    features = plan_config.get("features", [])
    limits = plan_config.get("limits", {"max_runs_per_day": 0, "max_horizon": 0})

    return BootstrapResponse(
        user=UserDTO(
            id=str(user.id),
            email=user.email,
            display_name=getattr(user, "full_name", None) or user.email.split("@")[0]
        ),
        subscription=SubscriptionDTO(
            has_active_plan=has_active_plan,
            plan_id=plan_id,
            status=sub_status,
            expires_at=expires_at,
            features=features,
            models_enabled=models_enabled,
            provider=provider
        ),
        limits=LimitsDTO(
            max_runs_per_day=limits.get("max_runs_per_day", 0),
            max_horizon=limits.get("max_horizon", 0)
        )
    )