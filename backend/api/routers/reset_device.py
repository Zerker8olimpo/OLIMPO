from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.database.models.user import User
from backend.database.models.device import Device
from backend.api.security.jwt import verify_google_id_token

router = APIRouter(prefix="/device", tags=["device"])

class ResetDeviceRequest(BaseModel):
    email: str
    id_token: str

@router.post("/reset")
def reset_device(data: ResetDeviceRequest, db: Session = Depends(get_db)):
    # 1. Validar Identidad
    try:
        user_info = verify_google_id_token(data.id_token)
        if user_info.get("email") != data.email:
            raise HTTPException(status_code=403, detail="Token email mismatch")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid identity: {str(e)}")

    # 2. Buscar Usuario
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Desactivar todos los dispositivos activos (Reset)
    db.query(Device).filter(Device.user_id == user.id).update({"is_active": False})
    db.commit()

    return {"status": "ok", "message": "Devices reset successfully"}