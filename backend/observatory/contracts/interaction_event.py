"""
Contrato principal del Observatorio Estadístico.

Este archivo define el esquema del evento observacional generado
POST-ejecución de cualquier modelo (EPSILON / SIGMA / POSEIDÓN).

INVARIANTES:
- Read-only
- Side-channel
- Fail-open
- No-interferencia decisional
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InputQuality(BaseModel):
    is_invalid: bool = False
    missing_fields: List[str] = []
    outlier_flags: List[str] = []
    inconsistency_flags: List[str] = []
    dq_penalty: float = Field(0.0, ge=0.0, le=1.0)


class RiskSnapshot(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_band: str
    drivers: Dict[str, float]
    contributions: Dict[str, float]
    top_drivers: List[str]


class HeliosGapSnapshot(BaseModel):
    gap_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    gap_fields: Optional[Dict[str, float]] = None
    twin_snapshot_id: Optional[str] = None
    twin_version: Optional[str] = None


class InteractionEvent(BaseModel):
    # Identidad
    event_id: str
    timestamp: datetime
    user_id_hash: str
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Contexto
    model_name: str
    product_key: str
    market_key: str
    app_version: str
    source: str  # mobile | web | api

    # Entradas del usuario
    inputs: Dict[str, float]

    # Calidad de entrada
    input_quality: InputQuality

    # Riesgo implícito
    risk_snapshot: RiskSnapshot

    # Contraste vs HELIOS (opcional)
    helios_gap: Optional[HeliosGapSnapshot] = None

    # Meta técnica
    latency_ms: Optional[int] = None
    request_id: Optional[str] = None
    server_node: Optional[str] = None
    errors: Optional[List[str]] = None

    class Config:
        frozen = True  # Garantiza inmutabilidad del evento
