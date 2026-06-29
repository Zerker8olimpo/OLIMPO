from typing import List, Dict, Any
from backend.agora.price_intelligence.source_adapters.base import PriceSourceAdapter

class ChileCompraAdapter(PriceSourceAdapter):
    """
    Adaptador para fuentes de ChileCompra / Mercado Público.
    """
    
    def __init__(self):
        super().__init__(source_id="chilecompra_api")

    def load(self, input_ref: Any, **kwargs) -> List[Dict[str, Any]]:
        # TODO: Implementar carga desde API de Mercado Público
        return []

    def normalize(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implementar normalización
        return raw_record

    def to_canonical(self, normalized_record: Dict[str, Any], family_context: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implementar transformación a canónico
        return normalized_record
