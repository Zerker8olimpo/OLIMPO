from fastapi import APIRouter, Depends

from core.security import get_current_user
from schemas.helios import HeliosSimulateRequest
from core.device_control import validate_device
from core.guards.subscription_guard import ensure_active_subscription
from core.plan_models import PLAN_MODELS, Plan
from core.errors import PlanNotAllowedError
from core.helios_runner import run_helios_simulation

router = APIRouter(prefix="/helios", tags=["Helios"])


@router.post("/simulate")
def simulate(
    payload: HeliosSimulateRequest,
    user = Depends(get_current_user),
    subs_store = Depends()
):
    # 1. Validar dispositivo
    validate_device(user.id, payload.device_id)

    # 2. Validar suscripción
    sub = ensure_active_subscription(user, subs_store)

    # 3. Validar modelo permitido por plan
    plan = Plan(sub["plan"])
    allowed_models = PLAN_MODELS[plan]

    if payload.model not in allowed_models:
        raise PlanNotAllowedError(
            model=payload.model,
            plan=plan.value
        )

    # 4. Ejecutar Helios
    return run_helios_simulation(payload)
