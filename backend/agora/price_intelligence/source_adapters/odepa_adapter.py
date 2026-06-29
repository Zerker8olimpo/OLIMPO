from typing import List, Dict, Any
from backend.agora.price_intelligence.source_adapters.base import PriceSourceAdapter

class OdepaAdapter(PriceSourceAdapter):
    """
    Adaptador para fuentes de ODEPA (Chile).
    """
    
    def __init__(self):
        super().__init__(source_id="odepa_mayoristas")

    def load(self, input_ref: Any, **kwargs) -> List[Dict[str, Any]]:
        # TODO: Implementar carga desde CSV/API de ODEPA
        return []

    def normalize(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implementar normalización
        return raw_record

    def to_canonical(self, normalized_record: Dict[str, Any], family_context: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implementar transformación a canónico
        return normalized_record
