from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access
from backend.api.schemas.model_run import ModelRunResponse

router = APIRouter(prefix="/poseidon", tags=["poseidon"])

@router.post("/run", response_model=ModelRunResponse)
def run_poseidon(
    payload: dict,
    claims: dict = Depends(require_model_access("poseidon"))
):
    """
    Endpoint para ejecutar el modelo POSEIDON.
    Disponible para planes: Enterprise.
    """
    return ModelRunResponse(
        kpis={"status": "success", "model": "poseidon", "plan_detectado": claims.get("plan")},
        warnings=[],
        interpretation="Modelo Poseidon ejecutado correctamente.",
        execution_metadata={
            "ts": datetime.now(timezone.utc).isoformat()
        },
    )