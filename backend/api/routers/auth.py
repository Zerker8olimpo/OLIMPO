from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.database.models.user import User
from backend.api.security.jwt import (
    verify_google_id_token,
    create_olimpo_jwt,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    id_token: str
    device_id: str  # ID único del hardware (Android ID / UUID)
    platform: str   # android / ios


@router.post("/google")
def auth_google(
    data: GoogleAuthRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    if not data.device_id or not data.platform:
        raise HTTPException(
            status_code=400,
            detail="device_id and platform are required"
        )

    # 1. Verificar Token con Google
    try:
        user_info = verify_google_id_token(data.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google Token: {str(e)}")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Token does not contain email")

    # 2. Buscar o Crear Usuario en DB
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Usuario nuevo: Lo creamos y vinculamos este dispositivo
        user = User(email=email, device_id=data.device_id, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Política de UN SOLO DISPOSITIVO
    # Si el usuario ya tiene device_id, debe coincidir con el que intenta entrar.
    if user.device_id and user.device_id != data.device_id:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "DEVICE_MISMATCH",
                "message": "Esta cuenta ya está vinculada a otro dispositivo. Contacte soporte para cambiarlo.",
            },
        )

    # Si el usuario existía pero no tenía dispositivo (ej: creado manualmente), lo vinculamos ahora.
    if not user.device_id:
        user.device_id = data.device_id
        db.add(user)
        db.commit()

    # 4. Generar JWT de sesión
    access_token = create_olimpo_jwt(user_info)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "id": user.id
        }
    }
