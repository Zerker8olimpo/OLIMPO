from fastapi import APIRouter
from backend.api.utils.helios_schema import HeliosInput, HeliosOutput
from backend.digital_twin.helios.HELIOS_SERVICE import run_helios

router = APIRouter(
    prefix="/helios",
    tags=["HELIOS Digital Twin"]
)

@router.post("/run", response_model=HeliosOutput)
def run_helios_endpoint(data: HeliosInput):
    return run_helios(data.dict())
