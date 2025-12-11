from fastapi import APIRouter
from backend.api.utils.sigma_schema import SigmaInput, SigmaOutput
from backend.digital_twin.sigma.SIGMA_SERVICE import run_sigma_service

router = APIRouter(
    prefix="/sigma",
    tags=["SIGMA"]
)

@router.post("/run", response_model=SigmaOutput)
def run_sigma_endpoint(data: SigmaInput):
    return run_sigma_service(data.dict())