from fastapi import APIRouter
from api.schemas.simulation import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()