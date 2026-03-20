"""
Interaction Event Builder
-------------------------

Construye el InteractionEvent inmutable del Observatorio Estadístico
usando exclusivamente información POST-ejecución.

INVARIANTES:
- Read-only
- Side-channel
- Fail-open
- No-interferencia decisional
"""

from datetime import datetime, UTC
from typing import Any, Dict, Optional
import uuid

from backend.observatory.contracts.interaction_event import (
    InteractionEvent,
    InputQuality,
    HeliosGapSnapshot,
)
from backend.observatory.contracts.risk_snapshot import RiskSnapshot
from backend.observatory.analytics.risk_calculator import RiskCalculator


class InteractionEventBuilder:
    """
    Ensambla un InteractionEvent completo y válido.
    """

    def __init__(self, cfg_quality: Dict, cfg_risk: Dict):
        self.cfg_quality = cfg_quality or {}
        self.cfg_risk = cfg_risk or {}

    def build(
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
    ) -> InteractionEvent:
        """
        Construye y retorna un InteractionEvent inmutable.
        Nunca lanza excepciones hacia arriba.
        """
        try:
            input_quality = self._build_input_quality(inputs)

            numeric_values = [
                float(v) for v in inputs.values()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]

            risk_snapshot = RiskCalculator.calculate_from_series(
                account_id=user_id_hash,
                values=numeric_values,
                observation_window=self.cfg_risk.get("observation_window", 12),
            )

            helios_gap = None
            if helios_gap_score is not None:
                helios_gap = HeliosGapSnapshot(
                    gap_score=helios_gap_score,
                    gap_fields=helios_gap_fields or {},
                    twin_snapshot_id=twin_snapshot_id,
                    twin_version=twin_version,
                )

            return InteractionEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(UTC),
                user_id_hash=user_id_hash,
                session_id=session_id,
                tenant_id=tenant_id,
                model_name=model_name,
                product_key=product_key,
                market_key=market_key,
                app_version=app_version,
                source=source,
                inputs=inputs,
                input_quality=input_quality,
                risk_snapshot=risk_snapshot,
                helios_gap=helios_gap,
                observatory_context=observatory_context or {},
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=None,
            )

        except Exception as exc:
            return InteractionEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(UTC),
                user_id_hash=user_id_hash,
                session_id=session_id,
                tenant_id=tenant_id,
                model_name=model_name,
                product_key=product_key,
                market_key=market_key,
                app_version=app_version,
                source=source,
                inputs=inputs,
                input_quality=InputQuality(
                    is_invalid=True,
                    missing_fields=[],
                    outlier_flags=[],
                    inconsistency_flags=[],
                    dq_penalty=1.0,
                ),
                risk_snapshot=RiskSnapshot(
                    account_id=user_id_hash,
                    risk_level="LOW",
                    risk_score=0.0,
                    volatility_index=0.0,
                    confidence=0.0,
                    observation_window=1,
                ),
                helios_gap=None,
                observatory_context={"builder_error": str(exc)},
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=[str(exc)],
            )

    def _build_input_quality(self, inputs: Dict[str, Any]) -> InputQuality:
        if not isinstance(inputs, dict):
            return InputQuality(
                is_invalid=True,
                missing_fields=[],
                outlier_flags=[],
                inconsistency_flags=["inputs_not_dict"],
                dq_penalty=1.0,
            )

        missing_fields = [str(k) for k, v in inputs.items() if v is None]
        outlier_flags = []
        inconsistency_flags = []

        for key, value in inputs.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try:
                    fv = float(value)
                    if abs(fv) > 1_000_000_000:
                        outlier_flags.append(str(key))
                except Exception:
                    inconsistency_flags.append(f"invalid_numeric:{key}")
            elif isinstance(value, list) and not value:
                inconsistency_flags.append(f"empty_series:{key}")

        penalty = min(1.0, (len(missing_fields) * 0.05) + (len(outlier_flags) * 0.03) + (len(inconsistency_flags) * 0.05))
        return InputQuality(
            is_invalid=penalty >= 0.8,
            missing_fields=missing_fields,
            outlier_flags=outlier_flags,
            inconsistency_flags=inconsistency_flags,
            dq_penalty=round(penalty, 4),
        )
