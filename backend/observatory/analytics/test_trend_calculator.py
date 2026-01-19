import pytest

from backend.observatory.analytics.trend_calculator import TrendCalculator


class TestTrendCalculator:
    def test_trend_up(self):
        """
        Serie claramente creciente → tendencia UP.
        """
        values = [10, 20, 30, 40, 50]

        snapshot = TrendCalculator.calculate_from_series(
            account_id="test_account",
            values=values,
            observation_window=len(values),
        )

        assert snapshot.trend_direction == "UP"
        assert snapshot.trend_strength > 0.0
        assert snapshot.slope > 0.0
        assert snapshot.confidence == 1.0

    def test_trend_down(self):
        """
        Serie claramente decreciente → tendencia DOWN.
        """
        values = [50, 40, 30, 20, 10]

        snapshot = TrendCalculator.calculate_from_series(
            account_id="test_account",
            values=values,
            observation_window=len(values),
        )

        assert snapshot.trend_direction == "DOWN"
        assert snapshot.trend_strength > 0.0
        assert snapshot.slope < 0.0
        assert snapshot.confidence == 1.0

    def test_trend_stable(self):
        """
        Serie estable → tendencia STABLE.
        """
        values = [100, 100, 100, 100, 100]

        snapshot = TrendCalculator.calculate_from_series(
            account_id="test_account",
            values=values,
            observation_window=len(values),
        )

        assert snapshot.trend_direction == "STABLE"
        assert snapshot.trend_strength == 0.0
        assert snapshot.slope == 0.0
        assert snapshot.confidence == 1.0

    def test_insufficient_data(self):
        """
        Con menos de 2 datos → STABLE, fuerza 0 y confianza 0.
        """
        values = [100]

        snapshot = TrendCalculator.calculate_from_series(
            account_id="test_account",
            values=values,
            observation_window=5,
        )

        assert snapshot.trend_direction == "STABLE"
        assert snapshot.trend_strength == 0.0
        assert snapshot.slope == 0.0
        assert snapshot.confidence == 0.0