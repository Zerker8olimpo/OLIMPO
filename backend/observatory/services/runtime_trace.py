from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


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
    applied_patches: List[Dict[str, Any]] = Field(default_factory=list)