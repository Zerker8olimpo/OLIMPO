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
        # En una implementación completa, aquí se inicializarían los analizadores.
        # Para mantener el builder puro y sin dependencias pesadas, solo guardamos config.
        self.cfg_quality = cfg_quality
        self.cfg_risk = cfg_risk

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
    ) -> InteractionEvent:
        """
        Construye y retorna un InteractionEvent inmutable.
        Nunca lanza excepciones hacia arriba.
        """
        try:
            # 1. Calidad de entrada (Stub / Default)
            # El builder estructura los datos, no ejecuta análisis pesado.
            input_quality = InputQuality(
                score=1.0,
                dq_penalty=0.0,
                issues=[],
                missing_fields=[]
            )

            # 2. Riesgo implícito (Calculado)
            # Extraemos valores numéricos de los inputs para medir volatilidad
            numeric_values = [
                float(v) for v in inputs.values() 
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]

            risk_snapshot = RiskCalculator.calculate_from_series(
                account_id=user_id_hash,
                values=numeric_values,
                observation_window=self.cfg_risk.get("observation_window", 12),
            )

            # 3. Gap vs HELIOS (opcional)
            helios_gap = None
            if helios_gap_score is not None:
                helios_gap = HeliosGapSnapshot(
                    gap_score=helios_gap_score,
                    gap_fields=helios_gap_fields or {},
                    twin_snapshot_id=twin_snapshot_id,
                    twin_version=twin_version,
                )

            # 4. Evento final
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
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=None,
            )

        except Exception as exc:
            # Fail-open absoluto: evento mínimo sin análisis
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
                input_quality=InputQuality(score=0.0, dq_penalty=0.0, issues=[], missing_fields=[]),
                risk_snapshot=RiskSnapshot(
                    account_id=user_id_hash,
                    risk_level="LOW",
                    risk_score=0.0,
                    volatility_index=0.0,
                    confidence=0.0,
                    observation_window=1,
                ),
                helios_gap=None,
                latency_ms=latency_ms,
                request_id=request_id,
                server_node=server_node,
                errors=[str(exc)],
            )
