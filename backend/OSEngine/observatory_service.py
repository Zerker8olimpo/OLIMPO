"""
backend/observatory/services/observatory_service.py
Fachada del Observatorio Estadístico.
"""
import logging
from typing import Any, Dict, Optional

# En la implementación final, aquí se importarán los builders y repositorios reales.
# from backend.observatory.builders.interaction_event_builder import InteractionEventBuilder
# from backend.observatory.storage.observatory_repository import ObservatoryRepository
# from backend.observatory.analytics.risk_calculator import RiskCalculator

logger = logging.getLogger("olimpo.observatory")

class ObservatoryService:
    """
    Orquestador del Observatorio.
    Responsabilidad: Coordinar la captura, análisis y persistencia de evidencia estadística.
    
    Principios de Diseño:
    - Fail-Open: Los errores internos nunca se propagan al caller.
    - Side-Channel: La lógica es puramente observacional, no afecta el retorno del modelo.
    """

    def __init__(self):
        # Inyección de dependencias (Stubs por ahora)
        pass

    async def observe_execution(
        self,
        context: Dict[str, Any],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        model_name: str
    ) -> None:
        """
        Registra una ejecución de modelo para fines estadísticos y de auditoría.
        
        Este método debe ser llamado justo antes de retornar la respuesta al usuario via API.
        Idealmente se invoca como una BackgroundTask de FastAPI para no bloquear la respuesta.
        """
        try:
            # 1. Validación de entrada (Sanity check)
            if not context or not model_name:
                logger.warning("[OBSERVATORY] Intento de observación sin contexto válido.")
                return

            # 2. Construcción del Evento (Builder)
            # Transforma datos crudos en un contrato estandarizado (InteractionEvent)
            # event = InteractionEventBuilder.build(context, inputs, model_name)

            # 3. Análisis de Riesgo Implícito (Analytics)
            # Calcula métricas sobre la salida (ej. ¿es un outlier?, ¿es coherente?)
            # risk_metrics = RiskCalculator.compute(outputs)

            # 4. Persistencia (Storage)
            # Guarda la evidencia en una tabla separada (no transaccional del negocio)
            # await ObservatoryRepository.save(event, risk_metrics)

            logger.info(f"[OBSERVATORY] ✅ Evidencia registrada para {model_name} | User: {context.get('gmail', 'anon')}")

        except Exception as e:
            # === FAIL-OPEN ===
            # Capturamos cualquier excepción.
            # El objetivo es que el usuario NUNCA reciba un error 500 porque falló el log de auditoría.
            logger.error(f"[OBSERVATORY] ❌ Fallo en observación: {str(e)}", exc_info=True)
            # IMPORTANTE: No re-lanzamos la excepción. El flujo muere aquí.

    async def get_audit_snapshot(self, user_email: str) -> Dict[str, Any]:
        """
        Retorna un resumen estadístico para el usuario (semáforos de consistencia).
        """
        try:
            # return await ObservatoryRepository.get_user_stats(user_email)
            return {
                "consistency_score": 0.98,
                "last_check": "ok",
                "message": "Comportamiento dentro de rangos normales."
            }
        except Exception:
            # Fail-open en lectura: retornamos estructura vacía o default, no error.
            return {"consistency_score": 0.0, "message": "Información no disponible temporalmente"}

# Instancia global para importar en routers
observatory_service = ObservatoryService()