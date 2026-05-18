from typing import Dict, Any, Optional

class MarginEngine:
    def process(self, current_price: float, projection: Dict[str, Any], unit_cost: Optional[float], user_price: Optional[float]) -> Dict[str, Any]:
        enabled = unit_cost is not None
        result = {"enabled": enabled}
        
        if enabled:
            result["unit_cost"] = unit_cost
            result["user_price"] = user_price
            
            if user_price:
                result["user_current_margin_percent"] = round((user_price - unit_cost) / user_price, 4)
            
            result["market_current_margin_percent"] = round((current_price - unit_cost) / current_price, 4)
            
            result["projected_margin_percent"] = {
                "low": round((projection["low"] - unit_cost) / projection["low"], 4),
                "base": round((projection["base"] - unit_cost) / projection["base"], 4),
                "high": round((projection["high"] - unit_cost) / projection["high"], 4)
            }
            
        return result
