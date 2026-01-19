import os
from pathlib import Path

from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

# ============================================================
# CARGA DE ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print("[CONFIG] .env cargado desde archivo")
else:
    print("[CONFIG] .env no encontrado, usando variables de entorno")

# ============================================================
# VARIABLES CRÍTICAS
# ============================================================

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET no configurada en .env")

APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="OLIMPO",
    version=APP_VERSION,
    description="API oficial OLIMPO",
)

# ============================================================
# MIDDLEWARE
# ============================================================

from backend.api.middleware.auth import JWTAuthMiddleware

app.add_middleware(JWTAuthMiddleware)

# ============================================================
# ROUTERS
# ============================================================

from backend.api.routers.auth import router as auth_router
from backend.api.routers.epsilon import router as epsilon_router
from backend.api.routers.sigma import router as sigma_router
from backend.api.routers.poseidon import router as poseidon_router
from backend.api.routers.helios import router as helios_router
from backend.api.routers.me import router as me_router
from backend.api.routers.billing_google import router as billing_google_router
from backend.api.routers.billing_mercadopago import router as billing_mercadopago_router
from backend.api.routers.admin import router as admin_router
from backend.api.routers.reset_device import router as reset_device_router
from backend.api.routers.account import router as account_router

app.include_router(auth_router)
app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)
app.include_router(me_router)
app.include_router(billing_google_router)
app.include_router(billing_mercadopago_router)
app.include_router(admin_router)
app.include_router(reset_device_router)
app.include_router(account_router)

# ============================================================
# HEALTH CHECK (IMPORTANTE PARA FLUTTER)
# ============================================================

class HealthResponse(BaseModel):
    status: str
    env: str
    version: str

@app.get("/health", tags=["system"], response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "env": APP_ENV,
        "version": APP_VERSION
    }
