from fastapi import APIRouter
from backend.api.utils.helios_schema import HeliosInput, HeliosOutput
from backend.models.helios.HELIOS_SERVICE import run_helios_service

router = APIRouter(
    prefix="/helios",
    tags=["HELIOS"]
)

@router.post("/run", response_model=HeliosOutput)
def run_helios_endpoint(data: HeliosInput):
    return run_helios_service(data.dict())