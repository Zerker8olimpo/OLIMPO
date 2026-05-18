from typing import Dict, Any

class ObservationEngine:
    def process(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        current = snapshot_data.get("current", {})
        return {
            "current_reference_price": current.get("price_median", 0),
            "price_min": current.get("price_min", 0),
            "price_median": current.get("price_median", 0),
            "price_avg": current.get("price_avg", 0),
            "price_max": current.get("price_max", 0),
            "historical_trend_percent": current.get("historical_trend_percent", 0),
            "volatility": current.get("volatility", 0),
            "sample_size": current.get("sample_size", 0),
            "last_update": current.get("last_update", "N/A")
        }
