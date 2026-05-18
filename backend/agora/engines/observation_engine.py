from typing import Dict, Any

class ObservationEngine:
    def process(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        current = snapshot_data.get("current", {})
        price_median = current.get("price_median")
        return {
            "current_reference_price": price_median if price_median and price_median > 0 else None,
            "price_min": current.get("price_min") if current.get("price_min") else None,
            "price_median": price_median if price_median and price_median > 0 else None,
            "price_avg": current.get("price_avg") if current.get("price_avg") else None,
            "price_max": current.get("price_max") if current.get("price_max") else None,
            "historical_trend_percent": current.get("historical_trend_percent", 0),
            "volatility": current.get("volatility", 0),
            "sample_size": current.get("sample_size", 0),
            "last_update": current.get("last_update", "N/A")
        }
