import os
from fastapi import Header, HTTPException, status
from backend.core.config import settings

def validate_agora_admin_token(x_agora_admin_token: str = Header(None)):
    """
    TAREA 1: Admin security simple.
    Valida el token de administración de ÁGORA desde la variable de entorno AGORA_ADMIN_TOKEN.
    """
    # En producción esto debería venir de un secret manager o env var segura
    expected_token = os.getenv("AGORA_ADMIN_TOKEN")
    
    if not expected_token:
        # Si no está configurado, el servicio admin no está disponible por seguridad
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGORA_ADMIN_TOKEN no está configurado en el servidor."
        )
        
    if not x_agora_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header X-AGORA-ADMIN-TOKEN."
        )
        
    if x_agora_admin_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de administración de ÁGORA inválido."
        )
    
    return True
