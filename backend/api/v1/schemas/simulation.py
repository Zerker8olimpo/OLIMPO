from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "OLIMPO"
    version: str = "0.1.0"

class ContextSchemaResponse(BaseModel):
    required_fields: List[str]
    optional_fields: List[str]

class SimulationRunRequest(BaseModel):
    producto: str = Field(..., examples=["tuberias_y_fittings_pvc_sanitario"])
    mercado: str = Field(..., examples=["mercado_sanitario_hidraulico"])
    demanda_actual: float = Field(..., ge=0)
    lead_time: float = Field(..., ge=0)
    stock_actual: float = Field(..., ge=0)

    # opcionales (si quieres usarlos después)
    variabilidad: Optional[float] = Field(default=None, ge=0)
    riesgo_aceptado: Optional[float] = Field(default=None, ge=0, le=1)

class SimulationRunResponse(BaseModel):
    run_id: str
    status: Literal["completed", "queued", "running"] = "completed"

class SimulationResultResponse(BaseModel):
    run_id: str
    producto: str
    mercado: str
    epsilon: Dict[str, Any]
    sigma: Dict[str, Any]
    risk_level: str

class AlertItem(BaseModel):
    level: Literal["info", "warning", "critical"]
    message: str
    confidence: float
    timestamp: str

class AlertsResponse(BaseModel):
    alerts: List[AlertItem]

class HistoryItem(BaseModel):
    run_id: str
    producto: str
    risk_level: str

class HistoryResponse(BaseModel):
    runs: List[HistoryItem]
