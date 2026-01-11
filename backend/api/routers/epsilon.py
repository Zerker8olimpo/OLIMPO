from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.api.utils.epsilon_schema import EpsilonInput, EpsilonOutput
from backend.database.models.user import User
from backend.database.models.subscription import Subscription
from backend.models.epsilon.EPSILON_SERVICE import run_epsilon_service

router = APIRouter(
    prefix="/epsilon",
    tags=["EPSILON"]
)

@router.post("/run", response_model=EpsilonOutput)
def run_epsilon_endpoint(
    data: EpsilonInput,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = db.query(User).filter(User.email == email).first()
    sub = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == "active").first() if user else None

    if not sub:
        raise HTTPException(status_code=403, detail="Active subscription required (Basic, Pro or Enterprise)")

    return run_epsilon_service(data.dict())