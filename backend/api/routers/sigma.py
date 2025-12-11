from fastapi import APIRouter
from api.utils.sigma_schema import SigmaInput, SigmaOutput
from models.sigma.SIGMA_SERVICE import run_sigma_service

router = APIRouter(
    prefix="/sigma",
    tags=["SIGMA"]
)


@router.post("/run", response_model=SigmaOutput)
def run_sigma(data: SigmaInput):
    """
    Endpoint oficial del modelo SIGMA.
    Ejecuta EOQ + ROP + Digital Twin + Montecarlo.
    """
    return run_sigma_service(data.dict())