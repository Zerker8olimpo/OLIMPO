from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.api.utils.helios_schema import HeliosInput, HeliosOutput
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.models.helios.HELIOS_SERVICE import run_helios_service

router = APIRouter(
    prefix="/helios",
    tags=["HELIOS"]
)

@router.post("/run", response_model=HeliosOutput)
def run_helios_endpoint(
    data: HeliosInput,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    device_id = claims.get("device_id")
    user = db.query(User).filter(User.email == email).first()
    sub = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.device_id == device_id,
        Subscription.status == "active"
    ).first() if user else None

    if not sub:
        raise HTTPException(status_code=403, detail="Active subscription required")

    if sub.plan_id != "enterprise":
        raise HTTPException(status_code=403, detail="ENTERPRISE plan required for full Digital Twin simulation")

    return run_helios_service(data.dict())