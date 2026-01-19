from fastapi import APIRouter, Depends
from backend.api.security.deps import require_model_access

router = APIRouter(prefix="/poseidon", tags=["poseidon"])

@router.post("/run")
def run_poseidon(
    payload: dict,
    claims: dict = Depends(require_model_access("poseidon"))
):
    """
    Endpoint para ejecutar el modelo POSEIDON.
    Disponible para planes: Enterprise.
    """
    return {
        "status": "success",
        "model": "poseidon",
        "message": "Modelo Poseidon ejecutado correctamente.",
        "plan_detectado": claims.get("plan")
    }