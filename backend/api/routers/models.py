from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.schemas.model_io import ModelRunRequest, ModelRunResponse
from backend.api.security.deps import get_current_claims
from backend.database.session import get_db
from backend.services.model_service import run_model_and_adapt
from backend.services.subscription_service import get_user_plan, check_entitlement

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/run", response_model=ModelRunResponse)
def run_models(
    req: ModelRunRequest,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db),
):
    """
    Endpoint unificado para EPSILON / SIGMA / POSEIDON.
    El adapter y validación viven en model_service.py
    """
    model = (req.modelName or "").strip().lower()
    user_id = claims.get("user_id")

    required = f"run_{model}"
    plan = get_user_plan(db, user_id, claims)

    if not check_entitlement(required, plan):
        raise HTTPException(
            status_code=403,
            detail={
                "action": "UPGRADE_PLAN",
                "message": "No tienes un plan activo o válido.",
                "requiredEntitlement": required,
            },
        )

    return run_model_and_adapt(
        model_name=model,
        params=req.modelParams,
    )