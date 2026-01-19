from typing import List
from statistics import mean
from math import isnan

from backend.observatory.contracts.trend_snapshot import TrendSnapshot


class TrendCalculator:
    """
    Calcula un TrendSnapshot estadístico a partir de una serie temporal.
    """

    @staticmethod
    def calculate_from_series(
        *,
        account_id: str,
        values: List[float],
        observation_window: int
    ) -> TrendSnapshot:
        """
        Detecta tendencia (UP / DOWN / STABLE) y su fuerza.
        """

        if not values or len(values) < 2:
            return TrendSnapshot(
                account_id=account_id,
                trend_direction="STABLE",
                trend_strength=0.0,
                slope=0.0,
                confidence=0.0,
                observation_window=observation_window,
            )

        n = len(values)
        x = list(range(n))
        y = values

        x_mean = mean(x)
        y_mean = mean(y)

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        # Normalización simple de fuerza
        trend_strength = min(abs(slope), 1.0)

        if abs(slope) < 0.01:
            direction = "STABLE"
        elif slope > 0:
            direction = "UP"
        else:
            direction = "DOWN"

        confidence = min(n / observation_window, 1.0)

        if isnan(slope):
            slope = 0.0
            trend_strength = 0.0
            direction = "STABLE"
            confidence = 0.0

        return TrendSnapshot(
            account_id=account_id,
            trend_direction=direction,
            trend_strength=trend_strength,
            slope=slope,
            confidence=confidence,
            observation_window=observation_window,
        )