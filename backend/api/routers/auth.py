from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.api.security.jwt import (
    verify_google_id_token,
    create_olimpo_jwt,
)
from backend.core.device_control import validate_device
from backend.core.errors import DeviceConflictError

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    id_token: str
    device_id: str
    platform: str


@router.post("/google")
def auth_google(data: GoogleAuthRequest, request: Request):
    if not data.device_id or not data.platform:
        raise HTTPException(
            status_code=400,
            detail="device_id and platform are required"
        )

    # ============================================================
    # VALIDACIÓN TOKEN GOOGLE
    # ============================================================

    user_info = verify_google_id_token(data.id_token)

    # ============================================================
    # CONTROL DE DISPOSITIVO
    # ============================================================

    try:
        validate_device(
            user_id=int(user_info["sub"]),  # mapeo temporal
            device_uuid=data.device_id,
            platform=data.platform,
            ip_address=request.client.host if request.client else None,
        )
    except DeviceConflictError:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "DEVICE_CONFLICT",
                "message": "La cuenta ya está activa en otro dispositivo",
            },
        )

    # ============================================================
    # GENERACIÓN JWT OLIMPO
    # ============================================================

    access_token = create_olimpo_jwt(user_info)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
