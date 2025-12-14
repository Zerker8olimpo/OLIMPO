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

from datetime import datetime
from typing import Dict, Optional
import uuid

from observatory.contracts.interaction_event import (
    InteractionEvent,
    InputQuality,
    HeliosGapSnapshot,
)
from observatory.contracts.risk_snapshot import RiskSnapshot
from observatory.quality.input_quality_analyzer import InputQualityAnalyzer
from observatory.risk.risk_engine import RiskEngine


class InteractionEventBuilder:
    """
    Ensambla un InteractionEvent completo y válido.
    """

    def __init__(self, cfg_quality: Dict, cfg_risk: Dict):
        self.quality_analyzer = InputQualityAnalyzer(cfg_quality)
        self.risk_engine = RiskEngine(cfg_risk)

    def build(
        self,
        *,
        user_id_hash: str,
        model_name: str,
        product_key: str,
        market_key: str,
        app_version: str,
        source: str,
        inputs: Dict[str, float],
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
    ) -> InteractionEvent:
        """
        Construye y retorna un InteractionEvent inmutable.
        Nunca lanza excepciones hacia arriba.
        """
        try:
            # 1. Calidad de entrada
            quality_dict = self.quality_analyzer.analyze(inputs)
            input_quality = InputQuality(**quality_dict)

            # 2. Riesgo implícito
            risk_snapshot: RiskSnapshot = self.risk_engine.compute(
                drivers=driver_values,
                dq_penalty=input_quality.dq_penalty,
                helios_gap_score=helios_gap_score,
            )

            # 3. Gap vs HELIOS (opcional)
            helios_gap = None
            if helios_gap_score is not None:
                helios_gap = HeliosGapSnapshot(
                    gap_score=helios_gap_score,
                    gap_fields=helios_gap_fields,
                    twin_snapshot_id=twin_snapshot_id,
                    twin_version=twin_version,
                )

            # 4. Evento final
            return InteractionEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
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
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=None,
            )

        except Exception as exc:
            # Fail-open absoluto: evento mínimo sin análisis
            return InteractionEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                user_id_hash=user_id_hash,
                session_id=session_id,
                tenant_id=tenant_id,
                model_name=model_name,
                product_key=product_key,
                market_key=market_key,
                app_version=app_version,
                source=source,
                inputs=inputs,
                input_quality=InputQuality(),
                risk_snapshot=RiskSnapshot(
                    risk_score=0.0,
                    risk_band="LOW",
                    drivers={},
                    weights={},
                    contributions={},
                    top_drivers=[],
                ),
                helios_gap=None,
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=[str(exc)],
            )
