"""
Observatory Storage Models
-------------------------

Modelos internos de persistencia del Observatorio Estadístico.

Estos modelos representan la **materialización almacenada** de la
información observacional. NO son contratos públicos ni snapshots
analíticos; son registros de estado versionables y gobernables.

INVARIANTES:
- Internos al Observatorio
- No decisionales
- No interacción con modelos core
- Aptos para persistencia (DB / Data Lake)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from observatory.contracts.interaction_event import InteractionEvent
from observatory.contracts.trend_snapshot import TrendSnapshot


# -------------------------------------------------
# Eventos observacionales persistidos
# -------------------------------------------------


@dataclass(frozen=True)
class ObservedEventRecord:
    """
    Representa un InteractionEvent persistido.

    Separa el contrato analítico (InteractionEvent) de su
    materialización en almacenamiento.
    """

    record_id: str
    created_at: datetime
    event: InteractionEvent
    contract_version: str = "v1"
    metadata: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------
# Tendencias persistidas (cache / histórico)
# -------------------------------------------------


@dataclass(frozen=True)
class UserTrendRecord:
    """
    Registro persistido de una tendencia por usuario.
    """

    record_id: str
    created_at: datetime
    snapshot: TrendSnapshot
    window_days: int
    contract_version: str = "v1"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketTrendRecord:
    """
    Registro persistido de una tendencia agregada de mercado.
    """

    record_id: str
    created_at: datetime
    snapshot: TrendSnapshot
    window_days: int
    contract_version: str = "v1"
    metadata: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------
# Helpers de creación
# -------------------------------------------------


def build_event_record(
    *,
    record_id: str,
    event: InteractionEvent,
    metadata: Optional[Dict[str, Any]] = None,
) -> ObservedEventRecord:
    """
    Construye un ObservedEventRecord de forma explícita.
    """
    return ObservedEventRecord(
        record_id=record_id,
        created_at=datetime.utcnow(),
        event=event,
        metadata=metadata or {},
    )


def build_user_trend_record(
    *,
    record_id: str,
    snapshot: TrendSnapshot,
    window_days: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> UserTrendRecord:
    """
    Construye un registro persistido de tendencia a nivel de usuario.
    """
    return UserTrendRecord(
        record_id=record_id,
        created_at=datetime.utcnow(),
        snapshot=snapshot,
        window_days=window_days,
        metadata=metadata or {},
    )


def build_market_trend_record(
    *,
    record_id: str,
    snapshot: TrendSnapshot,
    window_days: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> MarketTrendRecord:
    """
    Construye un registro persistido de tendencia agregada de mercado.
    """
    return MarketTrendRecord(
        record_id=record_id,
        created_at=datetime.utcnow(),
        snapshot=snapshot,
        window_days=window_days,
        metadata=metadata or {},
    )