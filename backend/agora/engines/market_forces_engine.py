from typing import Dict, Any

class MarketForcesEngine:
    def process(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        return snapshot_data.get("market_forces", {
            "supply": "desconocida",
            "demand": "desconocida",
            "substitutes": "desconocido"
        })
