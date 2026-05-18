from typing import List, Dict, Any

class QueryBuilder:
    """
    TAREA 3: Constructor de queries para búsqueda de precios.
    """
    
    def build_family_queries(
        self,
        market_id: str,
        product_id: str,
        family_id: str,
        family_cfg: Dict[str, Any]
    ) -> List[str]:
        """
        Construye una lista de términos de búsqueda optimizados para la familia.
        """
        queries = []
        
        # 1. Base query: frontend_label o family_nombre
        label = family_cfg.get("frontend_label")
        nombre = family_cfg.get("family_nombre")
        
        if label: queries.append(label)
        if nombre and nombre != label: queries.append(nombre)
        
        # 2. Agregar required terms si no están en la base
        req_terms = family_cfg.get("required_terms", [])
        if req_terms:
            req_str = " ".join(req_terms)
            if req_str not in queries:
                queries.append(req_str)
                
        # 3. Mezclar con atributos clave (diametro, medida, etc)
        # Tomamos los primeros 2 atributos para no explotar combinaciones
        attrs = family_cfg.get("attributes_for_matching", [])[:2]
        
        # Combinar la query base con attributes y required_terms
        base = label or nombre or " ".join(req_terms)
        
        if attrs:
            for attr in attrs:
                # Solo agregamos el nombre del atributo como pista
                q = f"{base} {attr}"
                if q not in queries:
                    queries.append(q)
                    
        # 4. Limitación y Limpieza
        # Máximo 5 queries únicas, mínimas 1
        seen = set()
        unique_queries = []
        for q in queries:
            q_clean = q.lower().strip()
            if q_clean and q_clean not in seen:
                unique_queries.append(q_clean)
                seen.add(q_clean)
                
        return unique_queries[:5]
