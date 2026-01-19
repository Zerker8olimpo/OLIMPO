from datetime import datetime, UTC
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class RiskSnapshot(BaseModel):
    """
    Snapshot estadístico de riesgo observado.
    No implica decisión ni recomendación.
    """

    account_id: str = Field(..., description="Identificador de la cuenta evaluada")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ..., description="Nivel de riesgo estadístico observado"
    )

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Score normalizado de riesgo [0,1]"
    )

    volatility_index: float = Field(
        ..., ge=0.0, description="Índice de volatilidad observada"
    )

    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confianza estadística del snapshot"
    )

    observation_window: int = Field(
        ..., description="Ventana temporal utilizada (en periodos)"
    )

    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp de la observación"
    )

    model_config = ConfigDict(frozen=True)
