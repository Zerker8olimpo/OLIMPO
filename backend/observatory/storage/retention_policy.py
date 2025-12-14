"""
Observatory Retention Policy
----------------------------

Define las políticas formales de retención, anonimización y purga de datos
para el Observatorio Estadístico de OLIMPO.

Este módulo NO elimina datos directamente ni ejecuta lógica destructiva;
solo define las reglas que otros componentes pueden aplicar.

INVARIANTES:
- Declarativo
- No decisional
- No dependencia de modelos core
- Orientado a compliance y ética de datos
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional


@dataclass(frozen=True)
class RetentionPolicy:
    """
    Política de retención para un tipo de dato observacional.
    """

    name: str
    retention_period: Optional[timedelta]
    anonymize_after: Optional[timedelta] = None
    aggregate_after: Optional[timedelta] = None
    description: Optional[str] = None

    def requires_anonymization(self) -> bool:
        return self.anonymize_after is not None

    def requires_aggregation(self) -> bool:
        return self.aggregate_after is not None


# -------------------------------------------------
# Políticas estándar del Observatorio
# -------------------------------------------------


EVENT_RETENTION_POLICY = RetentionPolicy(
    name="interaction_event",
    retention_period=timedelta(days=365),
    anonymize_after=timedelta(days=90),
    aggregate_after=timedelta(days=180),
    description="Eventos individuales de interacción con el sistema",
)


USER_TREND_RETENTION_POLICY = RetentionPolicy(
    name="user_trend",
    retention_period=timedelta(days=730),
    anonymize_after=None,
    aggregate_after=None,
    description="Tendencias longitudinales a nivel de usuario",
)


MARKET_TREND_RETENTION_POLICY = RetentionPolicy(
    name="market_trend",
    retention_period=None,  # Retención indefinida (solo agregado)
    anonymize_after=None,
    aggregate_after=None,
    description="Tendencias agregadas de mercado",
)
