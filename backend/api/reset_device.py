from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/device", tags=["device"])

class ResetDeviceRequest(BaseModel):
    email: str
    id_token: str  # Para validar identidad antes de resetear

@router.post("/reset")
def reset_device(data: ResetDeviceRequest):
    """
    Stub para reset_device.
    Funcionalidad futura:
    1. Validar identidad (Gmail + Token).
    2. Invalidar device_id anterior en DB (poner en NULL o borrar).
    3. Permitir que el próximo login registre el nuevo dispositivo.
    """
    return {
        "status": "ok",
        "message": "Dispositivo anterior desvinculado. Ahora puede ingresar con este dispositivo."
    }