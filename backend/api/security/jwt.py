from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException
import os
import jwt
from datetime import datetime, timedelta, timezone

JWT_ALGORITHM = "HS256"


# =========================
# HELPERS
# =========================

def _get_google_client_id() -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID not configured"
        )
    return client_id


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
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

def create_olimpo_jwt(user_info: dict) -> str:
    """
    Crea JWT propio de OLIMPO (HS256).
    Este es el token que debe ir en Authorization: Bearer <token>
    para /epsilon/run y cualquier endpoint protegido.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_info.get("sub", "")),
        "user_id": user_info.get("user_id"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "provider": "google",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }

    return jwt.encode(
        payload,
        _get_jwt_secret(),
        algorithm=JWT_ALGORITHM
    )


# Backward-compat: algunos módulos/imports antiguos usan este nombre
def create_access_token(user_info: dict) -> str:
    return create_olimpo_jwt(user_info)


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
