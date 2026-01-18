from fastapi import Header, HTTPException
from backend.api.security.jwt import verify_token


def get_current_claims(authorization: str = Header(default="")) -> dict:
    """
    Lee Authorization: Bearer <olimpo_jwt>
    Retorna claims: {"sub": "...", "email": "...", ...}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="MISSING_BEARER_TOKEN")

    token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="EMPTY_TOKEN")

    return verify_token(token)
