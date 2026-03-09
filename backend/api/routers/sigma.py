from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access
from backend.api.schemas.model_run import ModelRunResponse

router = APIRouter(prefix="/sigma", tags=["sigma"])

@router.post("/run", response_model=ModelRunResponse)
def run_sigma(
    payload: dict,
    claims: dict = Depends(require_model_access("sigma"))
):
    """
    Endpoint para ejecutar el modelo SIGMA.
    Disponible para planes: Pro, Enterprise.
    """
    return ModelRunResponse(
        kpis={"status": "success", "model": "sigma", "plan_detectado": claims.get("plan")},
        warnings=[],
        interpretation="Modelo Sigma ejecutado correctamente.",
        execution_metadata={
            "ts": datetime.now(timezone.utc).isoformat()
        },
    )