"""
Contrato formal del Risk Snapshot del Observatorio Estadístico.

Este modelo representa el riesgo implícito calculado POST-ejecución,
como metadato observacional. No interviene en decisiones ni modifica
resultados de los modelos core.

INVARIANTES:
- Read-only
- Side-channel
- Determinístico y explicable
- No-interferencia decisional
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class RiskDriverContribution(BaseModel):
    """
    Representa la contribución individual de un driver de riesgo.
    """
    driver: str
    value: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    contribution: float = Field(..., ge=0.0, le=1.0)


class RiskSnapshot(BaseModel):
    """
    Snapshot inmutable del riesgo implícito asociado a una decisión.
    """

    # Score global
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_band: str  # LOW | MEDIUM | HIGH | CRITICAL

    # Drivers
    drivers: Dict[str, float]
    weights: Dict[str, float]
    contributions: Dict[str, float]

    # Interpretabilidad
    top_drivers: List[str]

    class Config:
        frozen = True  # Garantiza inmutabilidad del snapshot
