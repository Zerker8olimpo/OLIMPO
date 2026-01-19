import os

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# from backend.api.security.jwt import verify_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de autenticación JWT para OLIMPO.
    En FASE 0 solo valida existencia de SECRET_KEY y
    deja pasar rutas públicas.
    """

    async def dispatch(self, request: Request, call_next):

        JWT_SECRET = os.getenv("JWT_SECRET")

        if not JWT_SECRET:
            return JSONResponse(
                status_code=500,
                content={"detail": "JWT_SECRET no configurada"}
            )

        # NOTA: La validación de seguridad se ha movido a Depends(get_current_claims)
        # en cada router individual para mayor granularidad.
        # Este middleware queda reservado para logging o inyección de contexto global si fuera necesario.

        return await call_next(request)
