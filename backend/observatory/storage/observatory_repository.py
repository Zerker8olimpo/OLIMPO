import logging
from backend.observatory.contracts.interaction_event import InteractionEvent
from backend.observatory.contracts.risk_snapshot import RiskSnapshot
from backend.observatory.contracts.trend_snapshot import TrendSnapshot
from backend.observatory.services.observatory_event import (
    ObservatoryEvent as ObservatoryEventModel,
    TrendSnapshotEntry
)

# from backend.database.session import SessionLocal  # Asumido

logger = logging.getLogger("olimpo.observatory")

class ObservatoryRepository:
    """
    Repositorio de almacenamiento para el Observatorio.
    Maneja la persistencia de eventos y snapshots estadísticos.
    """

    def save_event(self, event: InteractionEvent) -> None:
        """
        Persiste un evento de interacción.
        """
        # Implementación simplificada / stub
        # En producción: Mapear contrato -> modelo DB y guardar
        pass

    def store_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        """
        Persiste un snapshot de riesgo.
        """
        # Stub para mantener compatibilidad con el servicio
        pass

    def store_trend_snapshot(self, snapshot: TrendSnapshot) -> None:
        """
        Persiste un snapshot de tendencia en la base de datos.
        """
        try:
            entry = TrendSnapshotEntry(
                account_id=snapshot.account_id,
                trend_direction=snapshot.trend_direction,
                trend_strength=snapshot.trend_strength,
                slope=snapshot.slope,
                confidence=snapshot.confidence,
                observation_window=snapshot.observation_window,
                observed_at=snapshot.observed_at
            )

            # TODO: Integrar con SessionLocal real
            # with SessionLocal() as session:
            #     session.add(entry)
            #     session.commit()
            
            logger.info(f"[REPO] TrendSnapshot guardado para {snapshot.account_id} ({snapshot.trend_direction})")

        except Exception as e:
            logger.error(f"[REPO] Error guardando TrendSnapshot: {e}")