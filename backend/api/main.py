from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import settings

# DB
from backend.database.session import engine
from backend.database.base import Base
import backend.database.models  # importa package para registrar modelos existentes
Base.metadata.create_all(bind=engine)

# Routers existentes + nuevos
from backend.api.routers.auth_google import router as auth_router
from backend.api.routers.models import router as models_router
from backend.api.routers.subscriptions import router as subscriptions_router
from backend.api.routers.billing_google import router as billing_google_router
from backend.api.routers.bootstrap import router as bootstrap_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 403 and isinstance(exc.detail, dict) and "action" in exc.detail:
        return JSONResponse(status_code=403, content=exc.detail)

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/", tags=["system"])
def root():
    return {"status": "ok", "env": settings.APP_ENV, "version": settings.APP_VERSION}

app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(models_router)
app.include_router(bootstrap_router)
app.include_router(billing_google_router, tags=["Billing"])