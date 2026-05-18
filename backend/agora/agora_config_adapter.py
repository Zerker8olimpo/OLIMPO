import json
import os
from typing import Any, Dict, Optional

class AgoraConfigAdapter:
    def __init__(self, cfg_path: str = "backend/cfg"):
        self.cfg_path = cfg_path

    def _load_json(self, filename: str) -> Dict[str, Any]:
        full_path = os.path.join(self.cfg_path, filename)
        if not os.path.exists(full_path):
            return {}
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_markets(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_MARKETS.json")

    def get_products(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_PRODUCTS.json")

    def get_subfamilies(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_SUBFAMILIES.json")

    def get_indicators_cfg(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_INDICATORS.json")

    def get_projection_rules(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_PROJECTION_RULES.json")

    def get_commercial_rules(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_COMMERCIAL_INTERPRETATION.json")

    def get_snapshots(self) -> Dict[str, Any]:
        return self._load_json("CFG_AGORA_SAMPLE_SNAPSHOTS.json")
