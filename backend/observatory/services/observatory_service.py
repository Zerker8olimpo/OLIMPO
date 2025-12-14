"""
Observatory Service
-------------------

Fachada única del Observatorio Estadístico de OLIMPO.

Este servicio es el ÚNICO punto de integración con el pipeline del backend.
Opera como side-channel post–ejecución, garantizando aislamiento total,
fail-open y no-interferencia decisional.

INVARIANTES:
- Read-only
- Side-channel
- Fail-open (nunca bloquea el pipeline)
- No toca modelos, HELIOS ni OLIMPO Core
"""

from typing import Dict, Optional

from observatory.builders.interaction_event_builder import InteractionEventBuilder
from observatory.storage.observatory_repository import ObservatoryRepository


class ObservatoryService:
    """
    Fachada del Observatorio Estadístico.
    """

    def __init__(
        self,
        *,
        cfg_quality: Dict,
        cfg_risk: Dict,
        repository: ObservatoryRepository,
        enabled: bool = True,
    ):
        self.enabled = enabled
        self.builder = InteractionEventBuilder(
            cfg_quality=cfg_quality,
            cfg_risk=cfg_risk,
        )
        self.repository = repository

    # -------------------------------------------------
    # API pública (único punto de entrada)
    # -------------------------------------------------

    def log_interaction(
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
    ) -> None:
        """
        Registra una interacción observacional.

        Nunca lanza excepciones hacia el pipeline.
        Si el Observatorio está deshabilitado, no hace nada.
        """
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
            )

            # Persistencia (side-effect único permitido)
            self.repository.save_event(event)

        except Exception:
            # Fail-open absoluto: el pipeline nunca se entera
            return
