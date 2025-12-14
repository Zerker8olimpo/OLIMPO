"""
User Trend Analyzer
-------------------

Analiza tendencias longitudinales a nivel de usuario a partir de
InteractionEvent almacenados en el Observatorio.

INVARIANTES:
- Observacional
- Agregado (no evento individual)
- No decisional
- No retroalimentación a modelos
"""

from typing import Dict, List
from statistics import median

from observatory.contracts.interaction_event import InteractionEvent
from observatory.contracts.trend_snapshot import (
    TrendSnapshot,
    TrendWindow,
    InputTrendStats,
    QualityTrendStats,
    RiskTrendStats,
)


class UserTrendAnalyzer:
    """
    Construye TrendSnapshot a nivel usuario.
    """

    def __init__(self, window_days: int = 30):
        self.window_days = window_days

    # -------------------------------------------------
    # API pública
    # -------------------------------------------------

    def analyze(self, events: List[InteractionEvent]) -> List[TrendSnapshot]:
        """
        Analiza una lista de eventos y retorna snapshots de tendencia
        por usuario / producto / modelo.
        """
        snapshots: List[TrendSnapshot] = []

        # Agrupar eventos por (user, product, model)
        grouped = self._group_events(events)

        for (user_id, product_key, model_name), group_events in grouped.items():
            snapshot = self._build_snapshot(
                user_id=user_id,
                product_key=product_key,
                model_name=model_name,
                events=group_events,
            )
            snapshots.append(snapshot)

        return snapshots

    # -------------------------------------------------
    # Internos
    # -------------------------------------------------

    def _group_events(
        self, events: List[InteractionEvent]
    ) -> Dict[tuple, List[InteractionEvent]]:
        grouped: Dict[tuple, List[InteractionEvent]] = {}

        for event in events:
            key = (
                event.user_id_hash,
                event.product_key,
                event.model_name,
            )
            grouped.setdefault(key, []).append(event)

        return grouped

    def _build_snapshot(
        self,
        *,
        user_id: str,
        product_key: str,
        model_name: str,
        events: List[InteractionEvent],
    ) -> TrendSnapshot:
        """
        Construye un TrendSnapshot para un grupo de eventos homogéneos.
        """
        # Inputs
        input_stats = self._input_trends(events)

        # Calidad
        quality_stats = self._quality_trends(events)

        # Riesgo
        risk_stats = self._risk_trends(events)

        return TrendSnapshot(
            scope="user",
            scope_id=user_id,
            model_name=model_name,
            product_key=product_key,
            window=TrendWindow(
                window_days=self.window_days,
                n_events=len(events),
                n_users=1,
            ),
            input_trends=input_stats,
            quality_trends=quality_stats,
            risk_trends=risk_stats,
            gap_trends=None,
            last_updated=str(max(e.timestamp for e in events)),
        )

    # -------------------------------------------------
    # Cálculos estadísticos
    # -------------------------------------------------

    def _input_trends(self, events: List[InteractionEvent]) -> InputTrendStats:
        """
        Estadística robusta básica sobre inputs.
        """
        values: Dict[str, List[float]] = {}

        for e in events:
            for k, v in e.inputs.items():
                values.setdefault(k, []).append(v)

        medians = {k: median(v) for k, v in values.items() if v}
        iqr = {
            k: (max(v) - min(v)) if len(v) > 1 else 0.0
            for k, v in values.items()
        }
        p10 = {k: min(v) for k, v in values.items()}
        p90 = {k: max(v) for k, v in values.items()}

        return InputTrendStats(
            median=medians,
            iqr=iqr,
            p10=p10,
            p90=p90,
        )

    def _quality_trends(self, events: List[InteractionEvent]) -> QualityTrendStats:
        """
        Tendencias de calidad de entrada.
        """
        n = len(events)
        invalid = sum(1 for e in events if e.input_quality.is_invalid)
        outlier = sum(1 for e in events if e.input_quality.outlier_flags)
        incons = sum(1 for e in events if e.input_quality.inconsistency_flags)

        return QualityTrendStats(
            invalid_rate=invalid / n if n else 0.0,
            outlier_rate=outlier / n if n else 0.0,
            inconsistency_rate=incons / n if n else 0.0,
        )

    def _risk_trends(self, events: List[InteractionEvent]) -> RiskTrendStats:
        """
        Tendencias del riesgo implícito.
        """
        scores = [e.risk_snapshot.risk_score for e in events]

        band_dist: Dict[str, float] = {}
        for e in events:
            band = e.risk_snapshot.risk_band
            band_dist[band] = band_dist.get(band, 0) + 1

        n = len(events)
        band_dist = {k: v / n for k, v in band_dist.items()} if n else {}

        return RiskTrendStats(
            mean_risk=sum(scores) / n if n else 0.0,
            median_risk=median(scores) if scores else 0.0,
            max_risk=max(scores) if scores else 0.0,
            risk_band_distribution=band_dist,
            risk_drift=None,
        )
