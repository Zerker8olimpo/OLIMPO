import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de autenticación JWT para OLIMPO.
    En FASE 0 solo valida existencia de SECRET_KEY y
    deja pasar rutas públicas.
    """

    async def dispatch(self, request: Request, call_next):

        SECRET_KEY = os.getenv("SECRET_KEY")

        if not SECRET_KEY:
            return JSONResponse(
                status_code=500,
                content={"detail": "SECRET_KEY no configurada"}
            )

        # ============================================================
        # RUTAS PÚBLICAS (NO REQUIEREN AUTH)
        # ============================================================

        public_paths = (
            "/health",
            "/docs",
            "/openapi.json",
            "/auth",
            "/dev",
        )

        if request.url.path.startswith(public_paths):
            return await call_next(request)

        # ============================================================
        # JWT REAL (SE IMPLEMENTA EN FASE POSTERIOR)
        # ============================================================

        # Ejemplo futuro:
        # token = request.headers.get("Authorization")
        # validate_token(token, SECRET_KEY)

        return await call_next(request)
