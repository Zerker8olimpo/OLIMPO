from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access
from backend.api.schemas.model_run import ModelRunResponse

router = APIRouter(prefix="/epsilon", tags=["epsilon"])

@router.post("/run", response_model=ModelRunResponse)
def run_epsilon(
    payload: dict,
    claims: dict = Depends(require_model_access("epsilon"))
):
    """
    Endpoint para ejecutar el modelo EPSILON.
    Disponible para planes: Basic, Pro, Enterprise.
    """
    return ModelRunResponse(
        kpis={"status": "success", "model": "epsilon", "plan_detectado": claims.get("plan")},
        warnings=[],
        interpretation="Modelo Epsilon ejecutado correctamente.",
        execution_metadata={
            "ts": datetime.now(timezone.utc).isoformat()
        },
    )