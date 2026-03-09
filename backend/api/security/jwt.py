# backend/api/security/jwt.py
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta, timezone

from backend.core.config import settings

JWT_ALGORITHM = "HS256"


def _get_google_client_id() -> str:
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_OAUTH_CLIENT_ID not configured")
    return client_id


def _get_jwt_secret() -> str:
    secret = settings.JWT_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")
    return secret


def verify_google_id_token(token: str) -> dict:
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), _get_google_client_id())
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("Invalid issuer")
        return idinfo
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="INVALID_GOOGLE_TOKEN")


def create_access_token(
    *,
    sub: str,
    user_id: int,
    email: str,
    device_id: str,
    plan: str,
    test_mode: bool = False,
    expires_delta: timedelta | None = None,
) -> str:
    payload = {
        "sub": str(user_id),
        "google_sub": sub,
        "user_id": user_id,
        "email": email,
        "device_id": device_id,
        "plan": plan,          # ✅ ahora sí queda en el token (informativo)
        "test_mode": test_mode,
    }

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    payload["exp"] = expire

    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")
    except JWTError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")