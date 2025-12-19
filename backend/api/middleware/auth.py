from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from backend.api.security.jwt import verify_token

EXCLUDED_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/google",
    "/static",
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1) Rutas públicas (prefix match)
        if any(path == p or path.startswith(p + "/") or path.startswith(p) for p in EXCLUDED_PREFIXES):
            return await call_next(request)

        # 2) Header Authorization
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "NOT_AUTHENTICATED"},
            )

        token = auth_header.replace("Bearer ", "", 1).strip()

        # 3) Verificar JWT OLIMPO
        try:
            payload = verify_token(token)
            request.state.user = payload
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "INVALID_TOKEN"})

        return await call_next(request)
