from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.api.security.jwt import verify_token


security = HTTPBearer(auto_error=False)


def get_current_claims(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency que extrae y valida el JWT OLIMPO desde:
    Authorization: Bearer <token>
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="AUTHORIZATION_HEADER_MISSING"
        )

    token = credentials.credentials

    try:
        claims = verify_token(token)
        return claims
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="INVALID_AUTH_TOKEN"
        )
