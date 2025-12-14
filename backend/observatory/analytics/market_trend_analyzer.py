"""
Market Trend Analyzer
---------------------

Analiza tendencias agregadas a nivel de mercado a partir de
InteractionEvent almacenados en el Observatorio.

INVARIANTES:
- Observacional
- Agregado (colectivo)
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
    GapTrendStats,
)


class MarketTrendAnalyzer:
    """
    Construye TrendSnapshot a nivel de mercado / producto / modelo.
    """

    def __init__(self, window_days: int = 30):
        self.window_days = window_days

    # -------------------------------------------------
    # API pública
    # -------------------------------------------------

    def analyze(self, events: List[InteractionEvent]) -> List[TrendSnapshot]:
        """
        Analiza una lista de eventos y retorna snapshots de tendencia
        agregados por mercado / producto / modelo.
        """
        snapshots: List[TrendSnapshot] = []

        grouped = self._group_events(events)

        for (market_key, product_key, model_name), group_events in grouped.items():
            snapshot = self._build_snapshot(
                market_key=market_key,
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
                event.market_key,
                event.product_key,
                event.model_name,
            )
            grouped.setdefault(key, []).append(event)

        return grouped

    def _build_snapshot(
        self,
        *,
        market_key: str,
        product_key: str,
        model_name: str,
        events: List[InteractionEvent],
    ) -> TrendSnapshot:
        """
        Construye un TrendSnapshot agregado para un mercado.
        """
        input_stats = self._input_trends(events)
        quality_stats = self._quality_trends(events)
        risk_stats = self._risk_trends(events)
        gap_stats = self._gap_trends(events)

        return TrendSnapshot(
            scope="market",
            scope_id=market_key,
            model_name=model_name,
            product_key=product_key,
            window=TrendWindow(
                window_days=self.window_days,
                n_events=len(events),
                n_users=len({e.user_id_hash for e in events}),
            ),
            input_trends=input_stats,
            quality_trends=quality_stats,
            risk_trends=risk_stats,
            gap_trends=gap_stats,
            last_updated=str(max(e.timestamp for e in events)),
        )

    # -------------------------------------------------
    # Cálculos estadísticos
    # -------------------------------------------------

    def _input_trends(self, events: List[InteractionEvent]) -> InputTrendStats:
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

    def _gap_trends(self, events: List[InteractionEvent]) -> GapTrendStats:
        gaps = [
            e.helios_gap.gap_score
            for e in events
            if e.helios_gap and e.helios_gap.gap_score is not None
        ]

        if not gaps:
            return GapTrendStats(
                mean_gap=None,
                median_gap=None,
                high_gap_rate=None,
            )

        n = len(gaps)
        high_gap = sum(1 for g in gaps if g > 0.75)

        return GapTrendStats(
            mean_gap=sum(gaps) / n,
            median_gap=median(gaps),
            high_gap_rate=high_gap / n if n else 0.0,
        )
