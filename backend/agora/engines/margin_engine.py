from typing import Dict, Any, Optional

class MarginEngine:
    def process(self, current_price: Optional[float], projection: Dict[str, Any], unit_cost: Optional[float], user_price: Optional[float]) -> Dict[str, Any]:
        enabled = unit_cost is not None
        result = {"enabled": enabled}
        
        if enabled:
            result["unit_cost"] = unit_cost
            result["user_price"] = user_price
            
            if user_price:
                result["user_current_margin_percent"] = round((user_price - unit_cost) / user_price, 4) if user_price > 0 else None
            
            if current_price and current_price > 0:
                result["market_current_margin_percent"] = round((current_price - unit_cost) / current_price, 4)
            else:
                result["market_current_margin_percent"] = None
                
            proj_low = projection.get("low")
            proj_base = projection.get("base")
            proj_high = projection.get("high")
            
            if proj_low and proj_base and proj_high:
                result["projected_margin_percent"] = {
                    "low": round((proj_low - unit_cost) / proj_low, 4) if proj_low > 0 else None,
                    "base": round((proj_base - unit_cost) / proj_base, 4) if proj_base > 0 else None,
                    "high": round((proj_high - unit_cost) / proj_high, 4) if proj_high > 0 else None
                }
            else:
                result["projected_margin_percent"] = None
            
        return result
