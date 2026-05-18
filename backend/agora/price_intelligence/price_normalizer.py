import re
from typing import List, Dict, Any, Tuple, Optional
from backend.agora.family_catalog_service import FamilyCatalogService
from backend.agora.id_normalization_service import IdNormalizationService

class PriceNormalizer:
    def __init__(self):
        self.catalog = FamilyCatalogService()
        
    def _normalize_string(self, text: str) -> str:
        text = text.lower()
        # Remove accents
        text = re.sub(r'[áàäâ]', 'a', text)
        text = re.sub(r'[éèëê]', 'e', text)
        text = re.sub(r'[íìïî]', 'i', text)
        text = re.sub(r'[óòöô]', 'o', text)
        text = re.sub(r'[úùüû]', 'u', text)
        return text

    def normalize_price_item(
        self,
        raw_name: str,
        market_id: str,
        product_id: str
    ) -> Tuple[Optional[str], float, str]:
        """
        Devuelve: (family_id, confidence, reason)
        """
        c_market = self.catalog.resolve_market_id(market_id)
        c_product = self.catalog.resolve_product_id(c_market, product_id)
        
        families = self.catalog.list_families_by_product(c_market, c_product)
        if not families:
            return None, 0.0, "No families found for product"
            
        norm_name = self._normalize_string(raw_name)
        
        best_match = None
        highest_score = 0.0
        best_reason = ""
        
        for fam in families:
            score = 0.0
            exclude_hit = False
            
            # Check excludes
            for ext in fam.get("exclude_terms", []):
                if self._normalize_string(ext) in norm_name:
                    exclude_hit = True
                    break
            
            if exclude_hit:
                continue
                
            # Check required
            req_hits = 0
            req_terms = fam.get("required_terms", [])
            for req in req_terms:
                if self._normalize_string(req) in norm_name:
                    req_hits += 1
            
            if req_terms and req_hits < len(req_terms):
                continue # Missing required terms
                
            if req_terms:
                score += 0.5
                
            # Check includes
            inc_hits = 0
            inc_terms = fam.get("include_terms", [])
            for inc in inc_terms:
                if self._normalize_string(inc) in norm_name:
                    inc_hits += 1
                    
            if inc_terms:
                score += (inc_hits / len(inc_terms)) * 0.5
                
            if score > highest_score:
                highest_score = score
                best_match = fam["family_id"]
                best_reason = f"Matched {req_hits} req terms and {inc_hits} inc terms"
                
        if best_match and highest_score > 0.4:
            safe_family = IdNormalizationService.build_safe_id(best_match)
            return safe_family, highest_score, best_reason
            
        return None, 0.0, "No confident match found"

    def normalize_item_price_unit(
        self,
        item: Dict[str, Any],
        family_cfg: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normaliza el precio detectando si es un pack y calculando el precio unitario.
        """
        title = item.get("title", "").lower()
        price = item.get("price", 0.0)
        
        unit = "unidad"
        unit_price = price
        pack_size = 1
        
        # Detección simple de packs: "pack x10", "10 unidades", "caja 24"
        pack_patterns = [
            r'pack\s*x?\s*(\d+)',
            r'(\d+)\s*unidades',
            r'(\d+)\s*uds',
            r'caja\s*(\d+)',
            r'x\s*(\d+)\s*u'
        ]
        
        for pattern in pack_patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    pack_size = int(match.group(1))
                    if pack_size > 0:
                        unit = f"pack_{pack_size}"
                        unit_price = price / pack_size
                        break
                except ValueError:
                    continue
        
        return {
            "price": price,
            "currency": item.get("currency", "CLP"),
            "normalized_product_name": item.get("title"),
            "unit": unit,
            "normalized_unit_price": round(unit_price, 2),
            "pack_size": pack_size
        }
