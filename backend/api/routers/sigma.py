from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.api.utils.sigma_schema import SigmaInput, SigmaOutput
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.models.sigma.SIGMA_SERVICE import run_sigma_service

router = APIRouter(
    prefix="/sigma",
    tags=["SIGMA"]
)

@router.post("/run", response_model=SigmaOutput)
def run_sigma_endpoint(
    data: SigmaInput,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    sub = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == "active").first() if user else None

    if not sub:
        raise HTTPException(status_code=403, detail="Active subscription required")

    if sub.plan not in ["pro", "enterprise"]:
        raise HTTPException(status_code=403, detail="Plan PRO or ENTERPRISE required for Sigma model")

    return run_sigma_service(data.dict())