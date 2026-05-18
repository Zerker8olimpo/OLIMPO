from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class ObservationData(BaseModel):
    current_reference_price: float
    price_min: float
    price_median: float
    price_avg: float
    price_max: float
    historical_trend_percent: float
    volatility: float
    sample_size: int
    last_update: str

class ProjectionData(BaseModel):
    horizon_months: int
    low: float
    base: float
    high: float
    trend_label: str
    confidence: float

class EconomicIndicator(BaseModel):
    variation_6m: float
    impact: str
    direction: str

class MarketForces(BaseModel):
    supply: str
    demand: str
    substitutes: str

class MarginProjected(BaseModel):
    low: float
    base: float
    high: float

class MarginReference(BaseModel):
    enabled: bool
    unit_cost: Optional[float] = None
    user_price: Optional[float] = None
    user_current_margin_percent: Optional[float] = None
    market_current_margin_percent: Optional[float] = None
    projected_margin_percent: Optional[MarginProjected] = None

class CommercialInterpretation(BaseModel):
    market_position: str
    margin_health: str
    margin_risk: str
    suggested_signal: str
    message: str

class CfgContext(BaseModel):
    canonical_cfg_version: str
    canonical_cfg_hash: str
    agora_cfg_version: str
    agora_cfg_hash: str

class SnapshotContext(BaseModel):
    price_snapshot_id: str
    indicator_snapshot_id: str
    history_window_start: str
    history_window_end: str
    computed_at: datetime

class AgoraPulseResponse(BaseModel):
    module: str = "AGORA"
    market: str
    product: str
    subfamily: str
    history_window_months: int = 6
    projection_horizon_months: int
    observation: ObservationData
    projection: ProjectionData
    economic_indicators: Dict[str, EconomicIndicator]
    market_forces: MarketForces
    margin_reference: MarginReference
    commercial_interpretation: CommercialInterpretation
    cfg_context: CfgContext
    snapshot_context: SnapshotContext
    warnings: List[str] = []
