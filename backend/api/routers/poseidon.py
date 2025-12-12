from fastapi import APIRouter
from backend.api.utils.poseidon_schema import PoseidonInput, PoseidonOutput
from backend.models.poseidon.POSEIDON_SERVICE import run_poseidon_service

router = APIRouter(
    prefix="/poseidon",
    tags=["POSEIDON"]
)

@router.post("/run", response_model=PoseidonOutput)
def run_poseidon_endpoint(data: PoseidonInput):
    return run_poseidon_service(data.dict())