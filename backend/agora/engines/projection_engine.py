from typing import Dict, Any

class ProjectionEngine:
    def process(self, observation: Dict[str, Any], rules: Dict[str, Any], horizon: int) -> Dict[str, Any]:
        current_price = observation["current_reference_price"]
        hist_trend = observation["historical_trend_percent"] / 100.0
        
        horizon_rule = rules.get("horizons", {}).get(str(horizon), {"lambda_h": 1.0, "risk_multiplier": 1.0})
        default_rules = rules.get("default", {})
        
        lambda_h = horizon_rule["lambda_h"]
        risk_mult = horizon_rule["risk_multiplier"]
        risk_factor_base = default_rules.get("risk_factor_base", 0.05)
        cap_adj = default_rules.get("cap_adjustment", 0.25)
        
        # Fórmulas base simplificadas
        adjustment = lambda_h * hist_trend
        capped_adjustment = max(min(adjustment, cap_adj), -cap_adj)
        
        base_price = current_price * (1 + capped_adjustment)
        risk_factor = risk_factor_base * risk_mult
        
        low = base_price * (1 - risk_factor)
        high = base_price * (1 + risk_factor)
        
        trend_label = "alza_moderada" if capped_adjustment > 0.02 else "estable" if capped_adjustment > -0.02 else "baja_moderada"
        
        return {
            "horizon_months": horizon,
            "low": round(low, 2),
            "base": round(base_price, 2),
            "high": round(high, 2),
            "trend_label": trend_label,
            "confidence": 0.75 # Placeholder
        }
