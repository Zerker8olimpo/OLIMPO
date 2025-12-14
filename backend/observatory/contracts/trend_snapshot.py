"""
Contrato formal de Trend Snapshot del Observatorio Estadístico.

Este modelo representa una vista agregada y longitudinal de tendencias
observadas a partir de múltiples InteractionEvent.

INVARIANTES:
- Observacional
- Agregado (no evento individual)
- No decisional
- No retroalimentación a modelos
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TrendWindow(BaseModel):
    """
    Define una ventana temporal de análisis.
    """
    window_days: int = Field(..., gt=0)
    n_events: int = Field(..., ge=0)
    n_users: Optional[int] = Field(None, ge=0)


class InputTrendStats(BaseModel):
    """
    Estadística descriptiva robusta sobre inputs.
    """
    median: Dict[str, float]
    iqr: Dict[str, float]
    p10: Dict[str, float]
    p90: Dict[str, float]
    volatility: Optional[Dict[str, float]] = None
    drift: Optional[Dict[str, float]] = None


class QualityTrendStats(BaseModel):
    """
    Tendencias de calidad de entrada.
    """
    invalid_rate: float = Field(..., ge=0.0, le=1.0)
    outlier_rate: float = Field(..., ge=0.0, le=1.0)
    inconsistency_rate: float = Field(..., ge=0.0, le=1.0)


class RiskTrendStats(BaseModel):
    """
    Tendencias del riesgo implícito.
    """
    mean_risk: float = Field(..., ge=0.0, le=1.0)
    median_risk: float = Field(..., ge=0.0, le=1.0)
    max_risk: float = Field(..., ge=0.0, le=1.0)
    risk_band_distribution: Dict[str, float]
    risk_drift: Optional[float] = None


class GapTrendStats(BaseModel):
    """
    Tendencias de gap usuario vs HELIOS.
    """
    mean_gap: Optional[float] = Field(None, ge=0.0, le=1.0)
    median_gap: Optional[float] = Field(None, ge=0.0, le=1.0)
    high_gap_rate: Optional[float] = Field(None, ge=0.0, le=1.0)


class TrendSnapshot(BaseModel):
    """
    Snapshot inmutable de tendencia (usuario o mercado).
    """

    scope: str  # user | market
    scope_id: str  # user_id_hash o market_key
    model_name: str
    product_key: str

    window: TrendWindow

    input_trends: InputTrendStats
    quality_trends: QualityTrendStats
    risk_trends: RiskTrendStats
    gap_trends: Optional[GapTrendStats] = None

    last_updated: str

    class Config:
        frozen = True
