import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.api.db_deps import get_db
from backend.api.security.deps import get_current_claims
from backend.database.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

class ResetDeviceRequest(BaseModel):
    email: EmailStr

@router.post("/reset-device")
def reset_user_device(
    payload: ResetDeviceRequest,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    """
    Endpoint administrativo para desvincular el dispositivo de un usuario.
    Requiere que el solicitante esté en la lista ADMIN_EMAILS.
    """
    # 1. Verificación de permisos de administrador
    requester_email = claims.get("email")
    admin_emails_str = os.getenv("ADMIN_EMAILS", "")
    admin_emails = [e.strip() for e in admin_emails_str.split(",") if e.strip()]
    
    if requester_email not in admin_emails:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # 2. Buscar usuario objetivo
    target_user = db.query(User).filter(User.email == payload.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Resetear dispositivo
    target_user.device_id = None
    db.commit()

    return {
        "status": "success", 
        "message": f"Device ID desvinculado correctamente para {payload.email}"
    }

@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 100,
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_db)
):
    """
    Listar todos los usuarios y sus dispositivos vinculados.
    Requiere permisos de administrador.
    """
    # 1. Verificación de permisos de administrador
    requester_email = claims.get("email")
    admin_emails_str = os.getenv("ADMIN_EMAILS", "")
    admin_emails = [e.strip() for e in admin_emails_str.split(",") if e.strip()]
    
    if requester_email not in admin_emails:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    users = db.query(User).offset(skip).limit(limit).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "device_id": u.device_id,
            "is_active": u.is_active
        }
        for u in users
    ]