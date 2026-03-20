from __future__ import annotations

import logging
from typing import Any, Dict

from backend.database.models.observatory_event import ObservatoryEvent as ObservatoryEventModel
from backend.database.session import SessionLocal
from backend.observatory.contracts.interaction_event import InteractionEvent
from backend.observatory.contracts.risk_snapshot import RiskSnapshot
from backend.observatory.contracts.trend_snapshot import TrendSnapshot

logger = logging.getLogger("olimpo.observatory")


class ObservatoryRepository:
    """
    Repositorio de almacenamiento para el Observatorio.

    En esta etapa consolida una persistencia segura y compatible usando la tabla
    genérica `observatory_events`. Los snapshots especializados se almacenan como
    eventos tipados, evitando depender de tablas adicionales aún no migradas.
    """

    def save_event(self, event: InteractionEvent) -> None:
        payload = self._model_to_dict(event)
        record = ObservatoryEventModel(
            event_type="interaction_event",
            model_name=event.model_name,
            payload=payload,
            risk_score=float(event.risk_snapshot.risk_score),
            user_id=None,
        )
        self._commit(record, success_msg=f"[REPO] InteractionEvent guardado para {event.user_id_hash} ({event.model_name})")

    def store_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        payload = self._model_to_dict(snapshot)
        record = ObservatoryEventModel(
            event_type="risk_snapshot",
            model_name=None,
            payload=payload,
            risk_score=float(snapshot.risk_score),
            user_id=None,
        )
        self._commit(record, success_msg=f"[REPO] RiskSnapshot guardado para {snapshot.account_id} ({snapshot.risk_level})")

    def store_trend_snapshot(self, snapshot: TrendSnapshot) -> None:
        payload = self._model_to_dict(snapshot)
        record = ObservatoryEventModel(
            event_type="trend_snapshot",
            model_name=None,
            payload=payload,
            risk_score=None,
            user_id=None,
        )
        self._commit(record, success_msg=f"[REPO] TrendSnapshot guardado para {snapshot.account_id} ({snapshot.trend_direction})")

    def _commit(self, record: ObservatoryEventModel, *, success_msg: str) -> None:
        session = SessionLocal()
        try:
            session.add(record)
            session.commit()
            logger.info(success_msg)
        except Exception as exc:
            session.rollback()
            logger.error("[REPO] Error guardando evento observacional: %s", exc, exc_info=True)
        finally:
            session.close()

    def _model_to_dict(self, model: Any) -> Dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        if hasattr(model, "dict"):
            return model.dict()
        if isinstance(model, dict):
            return model
        return {"value": str(model)}
