import json
import os
from typing import Dict, Any, List, Optional
from backend.agora.price_intelligence.source_matrix import SourceMatrix

class SourceClassifier:
    """
    Clasifica familias de ÁGORA asignándoles fuentes de datos específicas
    basándose en la matriz de fuentes por mercado.
    """
    
    def __init__(self):
        self.matrix = SourceMatrix()

    def classify_family(self, market_id: str, product_id: str, family_id: str) -> Dict[str, Any]:
        """
        Determina la estrategia de fuente para una familia específica.
        """
        config = self.matrix.get_source_config(market_id)
        
        primary_source = config.get("primary_source_id", "manual_seed_admin")
        
        # Determinar status basado en la fuente asignada
        status = "ready"
        capture_mode = "automated"
        
        if primary_source in ["manual_seed_admin", "supplier_csv_admin"]:
            status = "manual_only"
            capture_mode = "manual"
        elif primary_source in ["mercado_libre_api"]:
            status = "ready" # Requiere auth pero está implementado
            capture_mode = "automated"
        elif primary_source in ["odepa_mayoristas", "odepa_consumidor", "cne_api"]:
            status = "ready" # Requiere adapter
            capture_mode = "automated"
        elif primary_source in ["banco_central_bde"]:
            status = "index_only"
            capture_mode = "automated"
        
        return {
            "family_id": family_id,
            "primary_source_id": primary_source,
            "secondary_source_ids": config.get("secondary_source_ids", []),
            "price_type": config.get("price_type", "unit_price"),
            "reliability_level": config.get("reliability_level", "low"),
            "source_status": status,
            "capture_mode": capture_mode,
            "automation_level": "high" if capture_mode == "automated" else "low"
        }

    def classify_all_families(self, cfg_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(cfg_path):
            return []
            
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            
        results = []
        for product in cfg.get("products", []):
            market_id = product.get("market_id")
            product_id = product.get("product_id")
            for family in product.get("families", []):
                family_id = family.get("family_id")
                classification = self.classify_family(market_id, product_id, family_id)
                classification["market_id"] = market_id
                classification["product_id"] = product_id
                results.append(classification)
                
        return results
