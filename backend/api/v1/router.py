from fastapi import APIRouter

from api.v1.endpoints.health import router as health_router
from api.v1.endpoints.context import router as context_router
from api.v1.endpoints.simulation import router as simulation_router
from api.v1.endpoints.alerts import router as alerts_router
from api.v1.endpoints.history import router as history_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(context_router, tags=["context"])
api_router.include_router(simulation_router, tags=["simulation"])
api_router.include_router(alerts_router, tags=["alerts"])
api_router.include_router(history_router, tags=["history"])