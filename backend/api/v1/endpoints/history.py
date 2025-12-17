from fastapi import APIRouter
from api.schemas.simulation import HistoryResponse, HistoryItem
from api.v1.endpoints.simulation import RUN_STORE  # reusa store MVP

router = APIRouter()

@router.get("/history", response_model=HistoryResponse)
def history(limit: int = 10):
    # orden simple por inserción (MVP). Luego puedes ordenar por created_at.
    items = list(RUN_STORE.values())[-limit:]
    runs = [
        HistoryItem(run_id=r["run_id"], producto=r["producto"], risk_level=r["risk_level"])
        for r in reversed(items)
    ]
    return HistoryResponse(runs=runs)