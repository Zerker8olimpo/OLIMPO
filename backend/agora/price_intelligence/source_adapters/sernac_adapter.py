from typing import List, Dict, Any
from backend.agora.price_intelligence.source_adapters.base import PriceSourceAdapter

class SernacAdapter(PriceSourceAdapter):
    def __init__(self):
        super().__init__(source_id="sernac_observatorio")

    def load(self, input_ref: Any, **kwargs) -> List[Dict[str, Any]]:
        return []

    def normalize(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return raw_record

    def to_canonical(self, normalized_record: Dict[str, Any], family_context: Dict[str, Any]) -> Dict[str, Any]:
        return normalized_record
