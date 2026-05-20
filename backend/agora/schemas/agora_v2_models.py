from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class AgoraV2MarketSummary(BaseModel):
    id: str
    safe_id: str
    market_id: str
    safe_market_id: str
    name: str
    frontend_label: str
    active: bool = True

class AgoraV2ProductSummary(BaseModel):
    id: str
    safe_id: str
    product_id: str
    safe_product_id: str
    market_id: str
    safe_market_id: str
    name: str
    product_nombre: str
    frontend_label: str
    families_count: int
    active: bool = True

class AgoraV2FamilySummary(BaseModel):
    family_id: str
    safe_id: str
    safe_family_id: str
    family_nombre: str
    frontend_label: str
    product_id: str
    safe_product_id: str
    market_id: str
    safe_market_id: str
    observation_unit: List[str]
    attributes_for_matching: List[str]
    include_terms: List[str]
    required_terms: List[str]
    exclude_terms: List[str]
    normalization_notes: List[str]
    has_snapshot_sample: bool
    has_real_snapshot: bool
    data_status: Literal["real_available", "sample_available", "fallback_available", "no_data"]

class AgoraV2Observation(BaseModel):
    current_reference_price: Optional[float] = None
    price_min: Optional[float] = None
    price_median: Optional[float] = None
    price_avg: Optional[float] = None
    price_max: Optional[float] = None
    historical_trend_percent: float = 0.0
    volatility: float = 0.0
    sample_size: int = 0
    last_update: str

class AgoraV2Projection(BaseModel):
    horizon_months: int
    low: Optional[float] = None
    base: Optional[float] = None
    high: Optional[float] = None
    trend_label: str
    confidence: float

class AgoraV2MarginReference(BaseModel):
    enabled: bool
    unit_cost: Optional[float] = None
    user_price: Optional[float] = None
    user_current_margin_percent: Optional[float] = None
    market_current_margin_percent: Optional[float] = None
    projected_margin_percent: Optional[Dict[str, float]] = None

class AgoraV2CommercialInterpretation(BaseModel):
    market_position: str
    margin_health: str
    margin_risk: str
    suggested_signal: str
    message: str

class AgoraV2HistoryCoverage(BaseModel):
    required_months: int = 6
    available_months: int
    missing_months: int
    history_status: Literal["none", "partial", "complete"]
    projection_quality: Literal["unavailable", "low", "medium", "usable"]

class AgoraV2SourceContext(BaseModel):
    source_mode: Literal["real", "sample", "fallback", "missing", "none"]
    real_web_observation: bool
    snapshot_date: Optional[str] = None
    historical_window_available: bool
    historical_backfill_months: int
    message: str
    is_sample_data: bool = False
    display_as_reference_only: bool = False
    coverage: Optional[AgoraV2HistoryCoverage] = None

class AgoraV2HistoryPoint(BaseModel):
    month_index: int
    label: str
    reference_price: float
    price_min: float
    price_median: float
    price_avg: float
    price_max: float
    confidence: float
    data_status: Literal["real_available", "sample_available", "fallback_available", "no_data"]

class AgoraV2ProjectionPoint(BaseModel):
    month_index: int
    label: str
    low: float
    base: float
    high: float
    confidence: float
    trend_label: str

class AgoraV2MarginProjectionPoint(BaseModel):
    month_index: int
    label: str
    margin_low: float
    margin_base: float
    margin_high: float

class AgoraV2CommercialPosition(BaseModel):
    current_cost: Optional[float] = None
    current_sale_price: Optional[float] = None
    current_margin_pct: Optional[float] = None
    market_reference_price: Optional[float] = None
    projected_market_price: Optional[float] = None
    market_trend_pct: Optional[float] = None
    market_position_now: str
    market_position_projected: str
    price_gap_pct: Optional[float] = None
    projected_gap_pct: Optional[float] = None
    margin_status: str
    commercial_risk: str
    recommendation: str
    confidence_level: float
    user_message: str

class AgoraV2PulseResponse(BaseModel):
    agora_enabled: bool = True
    plan_tier: str
    feature_depth: str
    data_mode: str
    history_status: str
    available_months: int
    required_months: int
    projection_quality: str
    allowed_horizons: List[int]
    requested_horizon: int
    effective_horizon: int
    horizon_adjusted: bool
    user_message: str
    admin_message: Optional[str] = None
    source_mix: Optional[Dict[str, Any]] = None
    last_snapshot_month: Optional[str] = None
    commercial_position: Optional[AgoraV2CommercialPosition] = None

    module: str = "AGORA"
    api_version: str = "v2"
    market_id: str
    safe_market_id: str
    product_id: str
    safe_product_id: str
    family_id: str
    safe_family_id: str
    history_window_months: int
    projection_horizon_months: int
    observation: AgoraV2Observation
    projection: AgoraV2Projection
    history_series: Optional[List[AgoraV2HistoryPoint]] = None
    projection_series: Optional[List[AgoraV2ProjectionPoint]] = None
    economic_indicators: Dict[str, Any]
    market_forces: Dict[str, Any]
    margin_reference: AgoraV2MarginReference
    margin_projection_series: Optional[List[AgoraV2MarginProjectionPoint]] = None
    commercial_interpretation: AgoraV2CommercialInterpretation
    cfg_context: Dict[str, Any]
    snapshot_context: Dict[str, Any]
    warnings: List[str] = []
    frontend_message: str
    data_status: Literal["real_available", "sample_available", "fallback_available", "no_data"]
    snapshot_status: Literal["real_snapshot", "sample_snapshot", "fallback_snapshot", "missing_snapshot"]
    source_context: AgoraV2SourceContext
    legacy_context: Optional[Dict[str, str]] = None

class AgoraV2ErrorResponse(BaseModel):
    error_code: str
    message: str
    received_id: Optional[Any] = None
    received_value: Optional[Any] = None
    suggestion: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    details: Optional[str] = None
