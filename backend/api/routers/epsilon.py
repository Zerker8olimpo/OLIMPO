from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access

router = APIRouter(prefix="/epsilon", tags=["epsilon"])

@router.post("/run")
def run_epsilon(
    payload: dict,
    claims: dict = Depends(require_model_access("epsilon"))
):
    """
    Endpoint para ejecutar el modelo EPSILON.
    Disponible para planes: Basic, Pro, Enterprise.
    """
    return {
        "status": "success",
        "model": "epsilon",
        "message": "Modelo Epsilon ejecutado correctamente.",
        "plan_detectado": claims.get("plan")
    }