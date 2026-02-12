from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import require_model_access
from backend.api.utils.helios_schema import HeliosInput, HeliosOutput
from backend.models.helios.HELIOS_SERVICE import run_helios_service

router = APIRouter(
    prefix="/helios",
    tags=["HELIOS"]
)

@router.post("/run", response_model=HeliosOutput)
def run_helios_endpoint(
    data: HeliosInput,
    # Autorización centralizada DB-First: Valida plan Enterprise/Helios
    claims: dict = Depends(require_model_access("helios")),
    db: Session = Depends(get_db)
):
    return run_helios_service(data.dict())