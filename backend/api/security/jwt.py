from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from backend.core.config import settings

JWT_ALGORITHM = "HS256"


# =========================
# HELPERS
# =========================

def _get_google_client_id() -> str:
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_OAUTH_CLIENT_ID not configured"
        )
    return client_id


def _get_jwt_secret() -> str:
    secret = settings.JWT_SECRET
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET not configured"
        )
    return secret


# =========================
# GOOGLE TOKEN
# =========================

def verify_google_id_token(token: str) -> dict:
    """
    Verifica id_token entregado por Google (GIS).
    Este token es RS256 y debe ser validado contra GOOGLE_CLIENT_ID.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            _get_google_client_id()
        )

        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("Invalid issuer")

        return idinfo

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="INVALID_GOOGLE_TOKEN"
        )


# =========================
# OLIMPO JWT
# =========================

def create_access_token(
    *,
    sub: str,
    user_id: int,
    email: str,
    device_id: str,
    plan: str,
    test_mode: bool = False,
    expires_delta: timedelta | None = None
) -> str:
    payload = {
        "sub": str(user_id),
        "google_sub": sub,
        "user_id": user_id,
        "email": email,
        "device_id": device_id,
        "plan": plan,
        "test_mode": test_mode,
    }

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    payload["exp"] = expire

    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """
    Verifica JWT OLIMPO (HS256) usado por el middleware.
    """
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM]
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")
