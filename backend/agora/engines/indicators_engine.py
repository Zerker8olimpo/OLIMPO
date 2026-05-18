from typing import Dict, Any

class IndicatorsEngine:
    def process(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        return snapshot_data.get("indicators", {})
