from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from backend.api.db_deps import get_db
from backend.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/device/reset")
def reset_device(
    email: str,
    db: Session = Depends(get_db),
):
    """
    Resetea el device_id del usuario para permitir login desde otro dispositivo.
    ⚠️ Este endpoint NO usa JWT.
    """

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Reset del device
    user.device_id = None
    logger.warning(f"[DEVICE RESET] user_email={email}")

    db.commit()

    return {"status": "device_reset_success"}