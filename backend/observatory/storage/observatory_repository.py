from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any, Dict

from backend.database.engine import engine
from backend.database.session import SessionLocal
from backend.database.base import Base
from backend.database.models.observatory_event import ObservatoryEvent
from backend.observatory.contracts.interaction_event import InteractionEvent
from backend.observatory.contracts.risk_snapshot import RiskSnapshot
from backend.observatory.contracts.trend_snapshot import TrendSnapshot

logger = logging.getLogger("olimpo.observatory")


def _to_payload(model: Any) -> Dict[str, Any]:
    if model is None:
        return {}
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if hasattr(model, "dict"):
        return model.dict()
    if isinstance(model, dict):
        return model
    return {"value": str(model)}


class ObservatoryRepository:
    """
    Repositorio de almacenamiento para el Observatorio.
    Persiste eventos y snapshots en la tabla genérica observatory_events.
    """

    def __init__(self) -> None:
        self._bootstrap_storage()

    def _bootstrap_storage(self) -> None:
        try:
            Base.metadata.create_all(bind=engine, tables=[ObservatoryEvent.__table__])
        except Exception as exc:
            logger.warning("[REPO] No fue posible bootstrap observatory_events: %s", exc, exc_info=True)

    def save_event(self, event: InteractionEvent) -> None:
        payload = _to_payload(event)
        entry = ObservatoryEvent(
            event_type="interaction_event",
            model_name=event.model_name,
            payload=payload,
            risk_score=float(event.risk_snapshot.risk_score),
            user_id=self._coerce_user_id(event.user_id_hash),
        )
        self._commit(entry, success_msg=f"[REPO] InteractionEvent guardado: {event.model_name}")

    def store_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        payload = _to_payload(snapshot)
        entry = ObservatoryEvent(
            event_type="risk_snapshot",
            model_name="OBSERVATORY",
            payload=payload,
            risk_score=float(snapshot.risk_score),
            user_id=self._coerce_user_id(snapshot.account_id),
        )
        self._commit(entry, success_msg=f"[REPO] RiskSnapshot guardado para {snapshot.account_id}")

    def store_trend_snapshot(self, snapshot: TrendSnapshot) -> None:
        payload = _to_payload(snapshot)
        entry = ObservatoryEvent(
            event_type="trend_snapshot",
            model_name="OBSERVATORY",
            payload=payload,
            risk_score=float(snapshot.trend_strength),
            user_id=self._coerce_user_id(snapshot.account_id),
        )
        self._commit(entry, success_msg=f"[REPO] TrendSnapshot guardado para {snapshot.account_id} ({snapshot.trend_direction})")

    def _commit(self, entry: ObservatoryEvent, *, success_msg: str) -> None:
        try:
            with SessionLocal() as session:
                session.add(entry)
                session.commit()
            logger.info(success_msg)
        except Exception as exc:
            logger.error("[REPO] Error guardando evento observacional: %s", exc, exc_info=True)

    def _coerce_user_id(self, value: Any) -> int | None:
        try:
            return int(value)
        except Exception:
            return None
