from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import settings

# -------------------------------------------------------
# DATABASE
# -------------------------------------------------------
from backend.database.session import engine
from backend.database.base import Base
import backend.database.models  # registra todos los modelos SQLAlchemy


# -------------------------------------------------------
# ROUTERS
# -------------------------------------------------------

# Auth
from backend.api.routers.auth_google import router as auth_router

# Models (EPSILON / SIGMA / POSEIDON)
from backend.api.routers.models import router as models_router

# Subscriptions
from backend.api.routers.subscriptions import router as subscriptions_router

# Billing
from backend.api.routers.billing_google import router as billing_google_router

# Bootstrap
from backend.api.routers.bootstrap import router as bootstrap_router

# System (health / ready)
from backend.api.routers.system import router as system_router

# ÁGORA
from backend.api.routers import agora
from backend.api.routers import agora_v2
from backend.api.routers import agora_admin

# Device Reset
from backend.api.routers.device_reset import router as device_reset_router

# Importación del router web (corregido desde 'routes' a 'routers')
from backend.api.routers.web_helios import router as web_helios_router

# Catalog
from backend.api.routers import catalog

# Web Billing
from backend.api.routers import web_billing

# -------------------------------------------------------
# FASTAPI APP
# -------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen para tu fase actual
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras (incluyendo Authorization)
)

# -------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# -------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):

    # Manejo especial para errores de autorización con acción
    if exc.status_code == 403 and isinstance(exc.detail, dict) and "action" in exc.detail:
        return JSONResponse(status_code=403, content=exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# -------------------------------------------------------
# ROOT ENDPOINT
# -------------------------------------------------------
@app.get("/", tags=["system"])
def root():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "version": settings.APP_VERSION,
    }


# -------------------------------------------------------
# REGISTER ROUTERS
# -------------------------------------------------------

# System endpoints
app.include_router(system_router)

# Auth
app.include_router(auth_router)

# Subscriptions
app.include_router(subscriptions_router)

# Models
app.include_router(models_router)

# Bootstrap
app.include_router(bootstrap_router)

# Billing
app.include_router(billing_google_router, tags=["Billing"])

# ÁGORA
app.include_router(agora.router)
app.include_router(agora_v2.router)
app.include_router(agora_admin.router)

# Device Reset

app.include_router(
    device_reset_router,
    prefix="/account",
    tags=["account"]
)

# Registro del router web
app.include_router(web_helios_router)

# Catalog
app.include_router(catalog.router)

# Web Billing
app.include_router(web_billing.router)