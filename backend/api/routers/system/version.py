from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(tags=["system"])

@router.get("/version")
def version():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }