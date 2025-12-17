from fastapi import APIRouter
from datetime import datetime, timezone
from api.schemas.simulation import AlertsResponse, AlertItem

router = APIRouter()

@router.get("/alerts", response_model=AlertsResponse)
def alerts():
    now = datetime.now(timezone.utc).isoformat()
    # MVP: placeholder. Luego lo conectas a tu AlertDispatcher real.
    return AlertsResponse(alerts=[
        AlertItem(level="warning", message="Impacto elevado detectado", confidence=0.78, timestamp=now)
    ])