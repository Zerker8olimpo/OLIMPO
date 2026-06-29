from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class PriceSourceAdapter(ABC):
    """
    Interfaz base para todos los adaptadores de fuentes de precios.
    """
    
    def __init__(self, source_id: str):
        self.source_id = source_id
        self.supports_dry_run = True
        self.requires_credentials = False

    @abstractmethod
    def load(self, input_ref: Any, **kwargs) -> List[Dict[str, Any]]:
        """
        Carga los datos crudos desde la fuente (archivo, API, etc).
        """
        pass

    @abstractmethod
    def normalize(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza un registro crudo al formato intermedio.
        """
        pass

    @abstractmethod
    def to_canonical(self, normalized_record: Dict[str, Any], family_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforma el registro normalizado al formato canónico universal de ÁGORA.
        """
        pass

    def validate(self, canonical_record: Dict[str, Any]) -> bool:
        """
        Validación básica del registro canónico.
        """
        required_fields = ["market_id", "product_id", "family_id", "observed_at", "price", "currency", "source_id"]
        for field in required_fields:
            if field not in canonical_record or canonical_record[field] is None:
                return False
        
        if canonical_record.get("price", 0) <= 0:
            return False
            
        return True
