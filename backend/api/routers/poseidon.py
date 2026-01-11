from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.api.utils.poseidon_schema import PoseidonInput, PoseidonOutput
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.models.poseidon.POSEIDON_SERVICE import run_poseidon_service

router = APIRouter(
    prefix="/poseidon",
    tags=["POSEIDON"]
)

@router.post("/run", response_model=PoseidonOutput)
def run_poseidon_endpoint(
    data: PoseidonInput,
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

    if sub.plan != "enterprise":
        raise HTTPException(status_code=403, detail="ENTERPRISE plan required for Poseidon model")

    return run_poseidon_service(data.dict())