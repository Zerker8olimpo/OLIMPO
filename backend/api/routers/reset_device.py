from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.database.models.user import User
from google.oauth2 import id_token
from google.auth.transport import requests

from backend.core.config import settings

router = APIRouter(prefix="/device", tags=["device"])


class ResetDeviceRequest(BaseModel):
    email: str
    id_token: str  # Para validar identidad antes de resetear


@router.post("/reset")
def reset_device(data: ResetDeviceRequest, db: Session = Depends(get_db)):
    """
    Permite desvincular el dispositivo actual asociado a un usuario.
    No modifica el modelo ni la arquitectura existente.
    """

    # 1️⃣ Validar token de Google para confirmar identidad
    try:
        idinfo = id_token.verify_oauth2_token(
            data.id_token,
            requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # 2️⃣ Verificar que el email del token coincide con el solicitado
    token_email = idinfo.get("email")
    if token_email != data.email:
        raise HTTPException(status_code=403, detail="Email mismatch")

    # 3️⃣ Buscar usuario en base de datos
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 4️⃣ Resetear dispositivo
    user.device_id = None

    db.commit()

    # 5️⃣ Respuesta (mantiene contrato existente)
    return {
        "status": "ok",
        "message": "Dispositivo anterior desvinculado. Ahora puede ingresar con este dispositivo."
    }