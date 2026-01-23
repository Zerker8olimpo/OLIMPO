# backend/api/main.py

from fastapi import FastAPI
from backend.core.config import settings

# Core
from backend.api.account import router as account_router
from backend.api.routers.reset_device import router as reset_device_router
from backend.api.routers.auth_google import router as auth_router
from backend.api.routers.me import router as me_router

# Billing
from backend.api.routers.billing_google import router as billing_google_router
from backend.api.routers.billing_mercadopago import router as billing_mp_router

# Models
from backend.api.routers.epsilon import router as epsilon_router
from backend.api.routers.sigma import router as sigma_router
from backend.api.routers.poseidon import router as poseidon_router
from backend.api.routers.helios import router as helios_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

@app.get("/", tags=["system"])
def root():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "version": settings.APP_VERSION,
    }

# Core
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(me_router)
app.include_router(reset_device_router)
app.include_router(billing_google_router)
app.include_router(billing_mp_router)
app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)
