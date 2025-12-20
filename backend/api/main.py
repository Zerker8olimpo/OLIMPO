from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pathlib import Path
from dotenv import load_dotenv
import os

# ======================================================
# CONFIGURACIÓN DE ENTORNO
# ======================================================

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    print("[CONFIG] .env cargado desde archivo")
else:
    print("[CONFIG] .env no encontrado, usando variables de entorno")

# 🔐 SECRET KEY (JWT / Seguridad)
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no configurada en variables de entorno")

APP_ENV = os.getenv("APP_ENV", "development")

# ======================================================
# APP
# ======================================================

app = FastAPI(
    title="OLIMPO",
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="API oficial OLIMPO",
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

if APP_ENV == "development":
    from backend.api.security.jwt import create_olimpo_jwt

    @app.get("/dev/token", tags=["dev"])
    def dev_token():
        """
        Endpoint SOLO para desarrollo.
        NO existe en producción.
        """
        return {
            "access_token": create_olimpo_jwt(
                payload={"sub": "dev_user", "role": "admin"},
                secret_key=SECRET_KEY
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
        version="1.0.0",
        description="API oficial OLIMPO",
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})

    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
