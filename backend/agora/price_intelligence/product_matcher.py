import re
from typing import List, Dict, Any, Tuple

class ProductMatcher:
    """
    TAREA 4: Motor de matching de items a familias.
    Valida si un item (ej: de Mercado Libre) corresponde realmente a la familia.
    """
    
    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        # Eliminar acentos
        text = re.sub(r'[áàäâ]', 'a', text)
        text = re.sub(r'[éèëê]', 'e', text)
        text = re.sub(r'[íìïî]', 'i', text)
        text = re.sub(r'[óòöô]', 'o', text)
        text = re.sub(r'[úùüû]', 'u', text)
        # Eliminar caracteres especiales básicos
        text = re.sub(r'[^a-z0-9 ]', ' ', text)
        return " ".join(text.split())

    def match_item_to_family(
        self,
        item: Dict[str, Any],
        family_cfg: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcula el score de coincidencia de un item con la familia.
        """
        title = self._normalize_text(item.get("title", ""))
        
        req_terms = [self._normalize_text(t) for t in family_cfg.get("required_terms", [])]
        inc_terms = [self._normalize_text(t) for t in family_cfg.get("include_terms", [])]
        exc_terms = [self._normalize_text(t) for t in family_cfg.get("exclude_terms", [])]
        
        matched_req = []
        missing_req = []
        matched_inc = []
        hit_exc = []
        
        # 1. Verificar Excluyentes (Filtro duro)
        for exc in exc_terms:
            if exc in title:
                hit_exc.append(exc)
        
        if hit_exc:
            return {
                "accepted": False,
                "score": 0.0,
                "reason": f"Hit exclude terms: {hit_exc}",
                "matched_terms": [],
                "excluded_terms": hit_exc
            }
            
        # 2. Verificar Requeridos (Filtro duro)
        for req in req_terms:
            if req in title:
                matched_req.append(req)
            else:
                missing_req.append(req)
                
        if missing_req:
            # Si faltan requeridos, el score es bajo y no se acepta
            return {
                "accepted": False,
                "score": 0.3 * (len(matched_req) / len(req_terms)) if req_terms else 0.0,
                "reason": f"Missing required terms: {missing_req}",
                "matched_terms": matched_req,
                "excluded_terms": []
            }
            
        # 3. Calcular Score Base (Ya tiene todos los requeridos)
        base_score = 0.70 # Starting point if all required match
        
        # 4. Sumar Include Terms
        for inc in inc_terms:
            if inc in title:
                matched_inc.append(inc)
                
        if inc_terms:
            inc_bonus = (len(matched_inc) / len(inc_terms)) * 0.25
            base_score += inc_bonus
            
        # 5. Bono por coincidencia exacta con frontend_label o nombre
        label = self._normalize_text(family_cfg.get("frontend_label", ""))
        nombre = self._normalize_text(family_cfg.get("family_nombre", ""))
        
        if label in title or nombre in title:
            base_score += 0.05
            
        final_score = min(1.0, base_score)
        
        return {
            "accepted": final_score >= 0.70,
            "score": round(final_score, 4),
            "reason": "Meets required terms and score threshold" if final_score >= 0.70 else "Score below threshold",
            "matched_terms": matched_req + matched_inc,
            "excluded_terms": []
        }
