from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

from api.schemas.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationResultResponse,
)

router = APIRouter()

# ✅ Store simple en memoria (MVP)
RUN_STORE: Dict[str, Dict[str, Any]] = {}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"

@router.post("/simulation/run", response_model=SimulationRunResponse)
def run_simulation(payload: SimulationRunRequest):
    """
    MVP:
    - Genera run_id
    - (Por ahora) simula resultado
    - En la siguiente iteración: aquí llamamos OSEngine/HELIOS real
    """
    run_id = _now_iso() + "_" + uuid.uuid4().hex[:8]

    # 🔁 Placeholder: aquí conectarás tu motor real
    # EJEMPLO de estructura de salida estable:
    epsilon = {
        "forecast": float(payload.demanda_actual) * 1.04,
        "confidence": 0.82,
    }
    sigma = {
        "rop": float(payload.stock_actual) + 150.0,
        "safety_stock": 300.0,
    }
    risk_score = 0.55
    result = {
        "run_id": run_id,
        "producto": payload.producto,
        "mercado": payload.mercado,
        "epsilon": epsilon,
        "sigma": sigma,
        "risk_level": _risk_level_from_score(risk_score),
        "created_at": _now_iso(),
    }

    RUN_STORE[run_id] = result
    return SimulationRunResponse(run_id=run_id, status="completed")

@router.get("/simulation/result/{run_id}", response_model=SimulationResultResponse)
def get_result(run_id: str):
    if run_id not in RUN_STORE:
        raise HTTPException(status_code=404, detail="run_id no encontrado")
    r = RUN_STORE[run_id]
    return SimulationResultResponse(
        run_id=r["run_id"],
        producto=r["producto"],
        mercado=r["mercado"],
        epsilon=r["epsilon"],
        sigma=r["sigma"],
        risk_level=r["risk_level"],
    )