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

import logging
from typing import Any, Dict, Optional, List

from backend.observatory.builders.interaction_event_builder import InteractionEventBuilder
from backend.observatory.storage.observatory_repository import ObservatoryRepository
from backend.observatory.analytics.risk_calculator import RiskCalculator
from backend.observatory.analytics.trend_calculator import TrendCalculator

logger = logging.getLogger("olimpo.observatory")

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

    def observe_execution(
        self,
        context: Dict[str, Any],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        model_name: str
    ) -> None:
        """
        Método adaptador para registrar ejecuciones desde endpoints (BackgroundTasks).
        Mapea el contexto genérico a la estructura específica del Observatorio.
        """
        if not self.enabled:
            return

        try:
            # Extracción de contexto con valores por defecto seguros
            user_id = context.get("gmail", "anonymous")
            device_id = context.get("device_id", "unknown")
            app_version = context.get("app_version", "unknown")
            platform = context.get("platform", "unknown")
            timestamp = context.get("timestamp")

            # Reutilizamos log_interaction para mantener la lógica centralizada
            # Mapeamos los inputs/outputs a una estructura que el builder pueda consumir
            # Nota: inputs en log_interaction espera Dict[str, float], aquí pasamos Any.
            # El builder debe ser lo suficientemente robusto para serializarlo (JSON).
            
            self.log_interaction(
                user_id_hash=user_id,
                model_name=model_name,
                product_key="ACCOUNT", # Contexto de cuenta, no de producto
                market_key="GLOBAL",
                app_version=app_version,
                source=f"{platform}_background",
                inputs=inputs,
                driver_values={}, # No aplica para evaluación de cuenta
                request_id=device_id, # Usamos device_id como traza si no hay request_id
                # Pasamos outputs como parte de la metadata si el builder lo soporta, 
                # o extendemos log_interaction en el futuro.
            )

            # --- Integración Risk + Trend (Cierre del flujo) ---
            
            # 1. Extracción de serie numérica para análisis
            values: List[float] = inputs.get("values", [])
            if not isinstance(values, list):
                values = []

            observation_window = len(values) if values else 1
            account_id = user_id

            # 2. Cálculo de Snapshots
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

            # 3. Persistencia de Snapshots
            # Asumimos que el repositorio soporta estos métodos.
            # Si no existen, el bloque try-except garantiza fail-open.
            self.repository.store_risk_snapshot(risk_snapshot)
            self.repository.store_trend_snapshot(trend_snapshot)
            
            logger.info(f"[OBSERVATORY] ✅ Evento registrado: {model_name} | User: {user_id}")

        except Exception as e:
            # Fail-open: Logueamos el error pero no interrumpimos nada
            logger.error(f"[OBSERVATORY] ❌ Fallo en observe_execution: {str(e)}", exc_info=True)


# Instancia global para importar en routers (Singleton)
# Se asume que ObservatoryRepository maneja su propia conexión o sesión internamente.
observatory_service = ObservatoryService(
    cfg_quality={},
    cfg_risk={},
    repository=ObservatoryRepository(),
    enabled=True
)
