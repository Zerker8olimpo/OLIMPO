import json
import os
from typing import Dict, Any, List, Optional

class SourceMatrix:
    """
    Gestiona el mapeo entre mercados y sus fuentes de precios recomendadas.
    """
    
    def __init__(self, matrix_path: str = "backend/agora/price_intelligence/source_matrix.json"):
        self.matrix_path = matrix_path
        self.matrix_data = self._load_matrix()

    def _load_matrix(self) -> Dict[str, Any]:
        if not os.path.exists(self.matrix_path):
            return {"markets": {}, "default_fallback": {}}
        
        with open(self.matrix_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_source_config(self, market_id: str) -> Dict[str, Any]:
        """
        Retorna la configuración de fuentes para un mercado específico.
        Si no existe, retorna el fallback por defecto.
        """
        markets = self.matrix_data.get("markets", {})
        if market_id in markets:
            return markets[market_id]
        
        return self.matrix_data.get("default_fallback", {})

    def get_primary_source(self, market_id: str) -> str:
        config = self.get_source_config(market_id)
        return config.get("primary_source_id", "manual_seed_admin")

    def get_secondary_sources(self, market_id: str) -> List[str]:
        config = self.get_source_config(market_id)
        return config.get("secondary_source_ids", [])

    def get_price_type(self, market_id: str) -> str:
        config = self.get_source_config(market_id)
        return config.get("price_type", "unit_price")

    def get_reliability_level(self, market_id: str) -> str:
        config = self.get_source_config(market_id)
        return config.get("reliability_level", "low")
