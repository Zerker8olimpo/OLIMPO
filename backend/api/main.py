from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configuración centralizada
from backend.core.config import settings

# Routers funcionales existentes
from backend.api.routers.epsilon import router as epsilon_router
from backend.api.routers.sigma import router as sigma_router
from backend.api.routers.poseidon import router as poseidon_router
from backend.api.routers.helios import router as helios_router
from backend.api.routers.user import router as user_router

# Routers técnicos (FASE 1)
from backend.api.routers.system.health import router as health_router
from backend.api.routers.system.version import router as version_router


# =========================
# Inicialización FastAPI
# =========================
app = FastAPI(
    title=settings.APP_NAME,
    description="API oficial para los modelos Epsilon, Sigma, Poseidón y el Digital Twin HELIOS",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# =========================
# Middleware CORS
# =========================
if settings.CORS_ORIGINS == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Endpoint raíz (status humano)
# =========================
@app.get("/", tags=["root"])
def root():
    return {
        "app": settings.APP_NAME,
        "status": "OK",
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "modules": [
            "Epsilon",
            "Sigma",
            "Poseidón",
            "HELIOS Digital Twin"
        ]
    }

# =========================
# Routers técnicos
# =========================
app.include_router(health_router)
app.include_router(version_router)

# =========================
# Routers funcionales
# =========================
app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)
app.include_router(user_router)
