import logging
import traceback

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config import settings

# from backend.api.security.jwt import verify_token

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de autenticación JWT para OLIMPO.
    En FASE 0 solo valida existencia de SECRET_KEY y
    deja pasar rutas públicas.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            JWT_SECRET = settings.JWT_SECRET

            if not JWT_SECRET:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "JWT_SECRET no configurada"}
                )

            # NOTA: La validación de seguridad se ha movido a Depends(get_current_claims)
            # en cada router individual para mayor granularidad.
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Middleware Crash: {e}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno en el Middleware de Autenticación", "message": str(e)}
            )
