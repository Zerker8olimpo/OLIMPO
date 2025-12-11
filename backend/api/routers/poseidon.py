from fastapi import APIRouter
from backend.api.utils.poseidon_schema import PoseidonInput, PoseidonOutput
from models.poseidon.POSEIDON_SERVICE import run_poseidon_service

router = APIRouter(
    prefix="/poseidon",
    tags=["POSEIDON"]
)


@router.post("/run", response_model=PoseidonOutput)
def run_poseidon(data: PoseidonInput):
    """
    Endpoint oficial del modelo POSEIDÓN.
    Ejecuta el doble tanque + Kalman + Digital Twin.
    """
    return run_poseidon_service(data.dict())