from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class TrendSnapshot(BaseModel):
    """
    Snapshot estadístico de tendencia observada.
    """

    account_id: str = Field(..., description="Identificador de la cuenta evaluada")

    trend_direction: Literal["UP", "DOWN", "STABLE"] = Field(
        ..., description="Dirección de la tendencia observada"
    )

    trend_strength: float = Field(
        ..., ge=0.0, le=1.0, description="Fuerza normalizada de la tendencia"
    )

    slope: float = Field(
        ..., description="Pendiente estadística estimada"
    )

    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confianza estadística del análisis"
    )

    observation_window: int = Field(
        ..., description="Ventana temporal utilizada (en periodos)"
    )

    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp de la observación"
    )

    model_config = ConfigDict(frozen=True)