from typing import Any, Dict, Optional


class ProjectionEngine:
    def process(
        self,
        observation: Dict[str, Any],
        rules: Dict[str, Any],
        horizon: int,
        indicators_result: Optional[Dict[str, Any]] = None,
        history_months: Optional[int] = None,
    ) -> Dict[str, Any]:
        current_price = observation.get("current_reference_price")

        if not current_price:
            return {
                "horizon_months": horizon,
                "low": None,
                "base": None,
                "high": None,
                "trend_label": "desconocida",
                "confidence": 0.0
            }

        hist_trend = observation.get("historical_trend_percent", 0.0) / 100.0

        horizon_rule = rules.get("horizons", {}).get(str(horizon), {"lambda_h": 1.0, "risk_multiplier": 1.0})
        default_rules = rules.get("default", {})

        lambda_h = horizon_rule["lambda_h"]
        risk_mult = horizon_rule["risk_multiplier"]
        risk_factor_base = default_rules.get("risk_factor_base", 0.05)
        cap_adj = default_rules.get("cap_adjustment", 0.25)
        indicator_weight = default_rules.get("indicator_weight", 0.3)

        # ec. 15 (simplificada): tendencia histórica ponderada por horizonte
        # más presión económica (E, ec. 23) calculada por IndicatorsEngine.
        economic_pressure = 0.0
        if indicators_result:
            pressure_index = indicators_result.get("economic_pressure_index")
            if pressure_index:
                economic_pressure = pressure_index.get("variation_6m") or 0.0

        adjustment = lambda_h * hist_trend + indicator_weight * economic_pressure
        capped_adjustment = max(min(adjustment, cap_adj), -cap_adj)

        base_price = current_price * (1 + capped_adjustment)
        risk_factor = risk_factor_base * risk_mult

        low = base_price * (1 - risk_factor)
        high = base_price * (1 + risk_factor)

        trend_label = "alza_moderada" if capped_adjustment > 0.02 else "estable" if capped_adjustment > -0.02 else "baja_moderada"

        confidence = self._compute_confidence(observation, default_rules, history_months)

        return {
            "horizon_months": horizon,
            "low": round(low, 2),
            "base": round(base_price, 2),
            "high": round(high, 2),
            "trend_label": trend_label,
            "confidence": confidence
        }

    def _compute_confidence(
        self,
        observation: Dict[str, Any],
        default_rules: Dict[str, Any],
        history_months: Optional[int],
    ) -> float:
        """
        Confianza (§12 de la maqueta) combinando:
        - Cn: confianza por tamaño de muestra del snapshot actual.
        - Ch: confianza por meses de historial disponibles (si se conocen;
          si no, se usa Cn como proxy único, degradando de forma honesta).
        """
        confidence_base = default_rules.get("confidence_base", 0.8)
        target_sample_size = default_rules.get("target_sample_size", 15)
        reference_history_months = default_rules.get("reference_history_months", 6)

        sample_size = observation.get("sample_size", 0) or 0
        cn = min(1.0, sample_size / target_sample_size) if target_sample_size else 1.0

        if history_months is not None and reference_history_months:
            ch = min(1.0, history_months / reference_history_months)
        else:
            ch = cn

        confidence = confidence_base * (0.5 * cn + 0.5 * ch)
        return round(max(0.1, min(0.95, confidence)), 4)
