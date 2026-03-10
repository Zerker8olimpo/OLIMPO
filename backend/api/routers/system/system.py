from fastapi import APIRouter
from sqlalchemy import text
from backend.database.session import SessionLocal

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check():
    """
    Simple liveness probe.
    Used by Render or monitoring tools to check if API is alive.
    """
    return {"status": "ok"}


@router.get("/ready")
def readiness_check():
    """
    Readiness probe.
    Verifies that the API can access its dependencies (database).
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()

        return {
            "status": "ready",
            "database": "ok"
        }

    except Exception as e:
        return {
            "status": "not_ready",
            "database": "error",
            "detail": str(e)
        }