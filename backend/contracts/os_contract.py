from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class Confidence(BaseModel):
    effective: float = 0.0
    psi: float = 0.0
    trend: float = 0.0
    external_min: float = 0.0
    external_mean: float = 0.0

class Guardrails(BaseModel):
    min_confidence_to_act: float = 0.60
    max_purchase_multiplier: float = 2.50
    min_purchase_multiplier: float = 0.70

class Multipliers(BaseModel):
    model_config = {"extra": "allow"}
    w_shock: float = 1.0
    w_volatility: float = 1.0
    w_comex: float = 1.0
    elasticity: float = 1.0

class RuntimeContext(BaseModel):
    multipliers: Multipliers = Field(default_factory=Multipliers)
    guardrails: Guardrails = Field(default_factory=Guardrails)
    flags: Dict[str, Any] = Field(default_factory=dict)

class TTLConfig(BaseModel):
    """Modelo anidado para soportar ttl.model_dump() invocado en el pipeline"""
    model_config = {"extra": "allow"}
    unit: str = "hours"
    value: int = 48

class OSContract(BaseModel):
    version: str = "OS_ENGINE_CONTRACT_1.1"
    os_state: str = "STABLE"
    decision_mode: str = "shadow"
    shadow_status: str = "shadow"
    model_name: Optional[str] = None
    confidence: Confidence = Field(default_factory=Confidence)
    signals_summary: Dict[str, Any] = Field(default_factory=dict)
    ttl: TTLConfig = Field(default_factory=TTLConfig)
    overlay_trace: Dict[str, Any] = Field(default_factory=dict)
    runtime_context: RuntimeContext = Field(default_factory=RuntimeContext)

    @property
    def effective_confidence(self) -> float:
        """Propiedad calculada requerida por el pipeline (_stamp_runtime_trace)"""
        return float(self.confidence.effective)

    def is_ttl_valid(self) -> bool:
        """Validación fail-open requerida por runtime_resolver"""
        return True