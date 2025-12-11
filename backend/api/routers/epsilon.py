from fastapi import APIRouter
from backend.api.utils.epsilon_schema import EpsilonInput, EpsilonOutput
from backend.digital_twin.epsilon.EPSILON_SERVICE import run_epsilon_service

router = APIRouter(
    prefix="/epsilon",
    tags=["EPSILON"]
)

@router.post("/run", response_model=EpsilonOutput)
def run_epsilon_endpoint(data: EpsilonInput):
    return run_epsilon_service(data.dict())