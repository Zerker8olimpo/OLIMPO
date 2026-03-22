from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PatchTrace(BaseModel):
    """
    Esquema tipado para cada mutación declarativa o regla evaluada.
    Diseñado en modo Fail-Open para no quebrar el request ante anomalías.
    """
    model_config = {"extra": "allow"}
    param: str = "unknown"
    rule: str = "unknown"
    source: str = "unknown"
    os_state: str = "UNKNOWN"
    applied: bool = False
    skip_reason: Optional[str] = None
    base: Any = None
    effective: Any = None
    multiplier: Any = None
    raw_multiplier: Any = None
    was_multiplier_clamped: Optional[bool] = None
    was_value_clamped: Optional[bool] = None
    clamp_limits: Dict[str, Any] = Field(default_factory=dict)
    rule_multiplier_limits: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None


class RuntimeTrace(BaseModel):
    """
    Huella de ejecución (Runtime Trace).
    Captura el contexto sistémico completo de una ejecución del modelo
    para garantizar auditabilidad y trazabilidad observacional.
    """
    trace_version: str = "1.1"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_name: str
    os_state: str
    decision_mode: str
    confidence: float
    shadow_status: str
    runtime_context_summary: Dict[str, Any]
    overlay_trace: Dict[str, Any]
    ttl: Dict[str, Any]
    helios_enriched: bool = True
    resolver_applied: bool
    applied_patches: List[PatchTrace] = Field(default_factory=list)