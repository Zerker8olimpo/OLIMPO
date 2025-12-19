# backend/api/main.py

from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi.openapi.utils import get_openapi
from backend.api.middleware.auth import JWTAuthMiddleware

# ======================================================
# CARGA FORZADA DEL .env
# ======================================================
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

if not ENV_PATH.exists():
    raise RuntimeError(f".env NO encontrado en {ENV_PATH}")

load_dotenv(dotenv_path=ENV_PATH, override=True)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET no está cargado desde .env")

# ======================================================
# APP
# ======================================================
app = FastAPI(
    title="OLIMPO",
    version=os.getenv("APP_VERSION", "1.0.0"),
)

# ======================================================
# MIDDLEWARE
# ======================================================
from backend.api.middleware.auth import JWTAuthMiddleware

app.add_middleware(JWTAuthMiddleware)

# ======================================================
# ROUTERS
# ======================================================
from backend.api.routers.auth import router as auth_router
from backend.api.routers.epsilon import router as epsilon_router
from backend.api.routers.sigma import router as sigma_router
from backend.api.routers.poseidon import router as poseidon_router
from backend.api.routers.helios import router as helios_router

app.include_router(auth_router)
app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)

# ======================================================
# DEV TOKEN (SOLO DESARROLLO)
# ======================================================
from backend.api.security.jwt import create_olimpo_jwt

APP_ENV = os.getenv("APP_ENV", "development")

if APP_ENV == "development":

    @app.get("/dev/token", tags=["dev"])
    def dev_token():
        """
        Endpoint SOLO para desarrollo.
        No existe en producción.
        """
        return {
            "access_token": create_olimpo_jwt(
                {"sub": "dev_user", "role": "admin"}
            )
        }

# ======================================================
# OPENAPI + SECURITY
# ======================================================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OLIMPO",
        version="1.0.0",  # ← NO usar app.version
        description="API oficial OLIMPO",
        routes=app.routes,
    )

    # Asegurar estructura base
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})

    # JWT Bearer
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
