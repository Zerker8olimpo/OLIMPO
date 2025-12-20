from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import os

class JWTAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        SECRET_KEY = os.getenv("SECRET_KEY")

        if not SECRET_KEY:
            return JSONResponse(
                status_code=500,
                content={"detail": "SECRET_KEY no configurada"}
            )

        # Rutas públicas
        if request.url.path.startswith("/docs") \
           or request.url.path.startswith("/openapi.json") \
           or request.url.path.startswith("/auth") \
           or request.url.path.startswith("/dev"):
            return await call_next(request)

        # Aquí va tu lógica JWT real
        # validate_token(request, SECRET_KEY)

        return await call_next(request)
