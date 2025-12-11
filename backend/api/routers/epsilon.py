from fastapi import APIRouter
from backend.api.utils.epsilon_schema import EpsilonInput, EpsilonOutput
from models.epsilon.EPSILON_SERVICE import run_epsilon_service

router = APIRouter(
    prefix="/epsilon",
    tags=["EPSILON"]
)


@router.post("/run", response_model=EpsilonOutput)
def run_epsilon(data: EpsilonInput):
    """
    Endpoint oficial del modelo EPSILON para OLIMPO.

    - Recibe datos desde la app móvil en formato JSON.
    - Ejecuta el Digital Twin (HELIOS) solo para EPSILON.
    - Retorna forecast_base, forecast_dt, p50, p95, compra sugerida, shocks y series internas.
    """
    return run_epsilon_service(data.dict())