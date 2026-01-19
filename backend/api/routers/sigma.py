from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access

router = APIRouter(prefix="/sigma", tags=["sigma"])

@router.post("/run")
def run_sigma(
    payload: dict,
    claims: dict = Depends(require_model_access("sigma"))
):
    """
    Endpoint para ejecutar el modelo SIGMA.
    Disponible para planes: Pro, Enterprise.
    """
    return {
        "status": "success",
        "model": "sigma",
        "message": "Modelo Sigma ejecutado correctamente.",
        "plan_detectado": claims.get("plan")
    }