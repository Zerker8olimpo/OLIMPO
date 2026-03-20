"""
Observatory Service
-------------------

Fachada única del Observatorio Estadístico de OLIMPO.

Este servicio es el ÚNICO punto de integración con el pipeline del backend.
Opera como side-channel post–ejecución, garantizando aislamiento total,
fail-open y no-interferencia decisional.
"""

import logging
from typing import Any, Dict, Optional, List

from backend.observatory.builders.interaction_event_builder import InteractionEventBuilder
from backend.observatory.storage.observatory_repository import ObservatoryRepository
from backend.observatory.analytics.risk_calculator import RiskCalculator
from backend.observatory.analytics.trend_calculator import TrendCalculator

logger = logging.getLogger("olimpo.observatory")


class ObservatoryService:
    def __init__(
        self,
        *,
        cfg_quality: Dict,
        cfg_risk: Dict,
        repository: ObservatoryRepository,
        enabled: bool = True,
    ):
        self.enabled = enabled
        self.builder = InteractionEventBuilder(cfg_quality=cfg_quality, cfg_risk=cfg_risk)
        self.repository = repository

    def log_interaction(
        self,
        *,
        user_id_hash: str,
        model_name: str,
        product_key: str,
        market_key: str,
        app_version: str,
        source: str,
        inputs: Dict[str, Any],
        driver_values: Dict[str, float],
        helios_gap_score: Optional[float] = None,
        helios_gap_fields: Optional[Dict[str, float]] = None,
        twin_snapshot_id: Optional[str] = None,
        twin_version: Optional[str] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        request_id: Optional[str] = None,
        server_node: Optional[str] = None,
        observatory_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        try:
            event = self.builder.build(
                user_id_hash=user_id_hash,
                model_name=model_name,
                product_key=product_key,
                market_key=market_key,
                app_version=app_version,
                source=source,
                inputs=inputs,
                driver_values=driver_values,
                helios_gap_score=helios_gap_score,
                helios_gap_fields=helios_gap_fields,
                twin_snapshot_id=twin_snapshot_id,
                twin_version=twin_version,
                session_id=session_id,
                tenant_id=tenant_id,
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                observatory_context=observatory_context,
            )
            self.repository.save_event(event)
        except Exception:
            return

    def observe_execution(
        self,
        context: Dict[str, Any],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        model_name: str,
        observatory_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        try:
            user_id = str(context.get("gmail") or context.get("user_id") or "anonymous")
            device_id = str(context.get("device_id") or "unknown")
            app_version = str(context.get("app_version") or "unknown")
            platform = str(context.get("platform") or "unknown")
            product_key = str(context.get("product_id") or inputs.get("product_id") or "ACCOUNT")
            market_key = str(context.get("market_id") or inputs.get("market_id") or "GLOBAL")

            merged_context = self._merge_observatory_context(observatory_context, inputs, outputs)

            self.log_interaction(
                user_id_hash=user_id,
                model_name=model_name,
                product_key=product_key,
                market_key=market_key,
                app_version=app_version,
                source=f"{platform}_background",
                inputs=inputs,
                driver_values={},
                request_id=device_id,
                observatory_context=merged_context,
            )

            values: List[float] = self._extract_values(inputs, outputs)
            observation_window = len(values) if values else 1
            account_id = user_id

            risk_snapshot = RiskCalculator.calculate_from_series(
                account_id=account_id,
                values=values,
                observation_window=observation_window,
            )
            trend_snapshot = TrendCalculator.calculate_from_series(
                account_id=account_id,
                values=values,
                observation_window=observation_window,
            )

            self.repository.store_risk_snapshot(risk_snapshot)
            self.repository.store_trend_snapshot(trend_snapshot)
            logger.info("[OBSERVATORY] ✅ Evento registrado: %s | User: %s", model_name, user_id)
        except Exception as e:
            logger.error("[OBSERVATORY] ❌ Fallo en observe_execution: %s", str(e), exc_info=True)

    def _merge_observatory_context(
        self,
        observatory_context: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = dict(observatory_context or {})
        context.setdefault("input_keys", sorted([str(k) for k in inputs.keys()])[:50])
        context.setdefault("output_keys", sorted([str(k) for k in outputs.keys()])[:50])
        context.setdefault("input_series_length", len(inputs.get("demanda_historica", []) or []))
        return context

    def _extract_values(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> List[float]:
        raw = inputs.get("values")
        if isinstance(raw, list):
            return [float(v) for v in raw if isinstance(v, (int, float)) and not isinstance(v, bool)]

        demanda = inputs.get("demanda_historica")
        if isinstance(demanda, list):
            return [float(v) for v in demanda if isinstance(v, (int, float)) and not isinstance(v, bool)]

        expected = outputs.get("expected") if isinstance(outputs, dict) else None
        if isinstance(expected, list):
            return [float(v) for v in expected if isinstance(v, (int, float)) and not isinstance(v, bool)]

        return []


observatory_service = ObservatoryService(
    cfg_quality={},
    cfg_risk={},
    repository=ObservatoryRepository(),
    enabled=True,
)
