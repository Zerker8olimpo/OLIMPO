from fastapi import APIRouter, Depends
from backend.api.security.deps import get_current_claims

router = APIRouter()

@router.get("/me")
def account_me(claims = Depends(get_current_claims)):
    return {
        "status": "ok",
        "user": claims
    }
