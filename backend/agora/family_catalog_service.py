import json
import os
from backend.agora.id_normalization_service import IdNormalizationService

class FamilyCatalogService:
    def __init__(self, cfg_path: str = "backend/cfg/CFG_AGORA_PRODUCT_FAMILIES.json"):
        self.data = {}
        self.snapshot_path = "backend/cfg/CFG_AGORA_FAMILY_SNAPSHOTS_SAMPLE.json"
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

    def _get_available_snapshot_ids(self) -> set:
        if not os.path.exists(self.snapshot_path):
            return set()
        try:
            with open(self.snapshot_path, 'r', encoding='utf-8') as f:
                snaps = json.load(f).get("snapshots", [])
                return {s.get("family_id") for s in snaps}
        except:
            return set()

    def list_markets_from_families(self):
        markets = {}
        for p in self.data.get("products", []):
            m_id = p.get("market_id")
            if m_id not in markets:
                safe_id = IdNormalizationService.build_safe_id(m_id)
                m_nombre = p.get("market_nombre")
                markets[m_id] = {
                    "id": m_id,
                    "safe_id": safe_id,
                    "market_id": m_id,
                    "safe_market_id": safe_id,
                    "name": m_nombre,
                    "frontend_label": m_nombre,
                    "active": True
                }
        return list(markets.values())

    def resolve_market_id(self, market_id: str) -> str:
        markets = self.list_markets_from_families()
        for m in markets:
            if m["id"] == market_id or m["safe_id"] == market_id:
                return m["id"]
        return market_id

    def list_products_by_market(self, market_id: str):
        m_id_canonical = self.resolve_market_id(market_id)
        products = []
        for p in self.data.get("products", []):
            if p.get("market_id") == m_id_canonical:
                p_id = p.get("product_id")
                safe_id = IdNormalizationService.build_safe_id(p_id)
                p_nombre = p.get("product_nombre")
                products.append({
                    "id": p_id,
                    "safe_id": safe_id,
                    "product_id": p_id,
                    "safe_product_id": safe_id,
                    "market_id": m_id_canonical,
                    "safe_market_id": IdNormalizationService.build_safe_id(m_id_canonical),
                    "name": p_nombre,
                    "product_nombre": p_nombre,
                    "frontend_label": p_nombre,
                    "families_count": len(p.get("families", [])),
                    "active": True
                })
        return products

    def resolve_product_id(self, market_id: str, product_id: str) -> str:
        m_id_canonical = self.resolve_market_id(market_id)
        products = self.list_products_by_market(m_id_canonical)
        for p in products:
            if p["id"] == product_id or p["safe_id"] == product_id:
                return p["id"]
        return product_id

    def list_families_by_product(self, market_id: str, product_id: str):
        m_id_canonical = self.resolve_market_id(market_id)
        p_id_canonical = self.resolve_product_id(m_id_canonical, product_id)
        
        snapshot_ids = self._get_available_snapshot_ids()
        safe_m_id = IdNormalizationService.build_safe_id(m_id_canonical)
        safe_p_id = IdNormalizationService.build_safe_id(p_id_canonical)
        
        for p in self.data.get("products", []):
            if p.get("market_id") == m_id_canonical and p.get("product_id") == p_id_canonical:
                families = []
                for f in p.get("families", []):
                    f_id = f.get("family_id")
                    safe_f_id = IdNormalizationService.build_safe_id(f_id)
                    has_snap = f_id in snapshot_ids
                    f_nombre = f.get("family_nombre")
                    
                    family_summary = {
                        "family_id": f_id,
                        "safe_id": safe_f_id,
                        "safe_family_id": safe_f_id,
                        "family_nombre": f_nombre,
                        "frontend_label": f_nombre.title(),
                        "product_id": p_id_canonical,
                        "safe_product_id": safe_p_id,
                        "market_id": m_id_canonical,
                        "safe_market_id": safe_m_id,
                        "observation_unit": f.get("observation_unit", []),
                        "attributes_for_matching": f.get("attributes_for_matching", []),
                        "include_terms": f.get("include_terms", []),
                        "required_terms": f.get("required_terms", []),
                        "exclude_terms": f.get("exclude_terms", []),
                        "normalization_notes": f.get("normalization_notes", []),
                        "has_snapshot_sample": has_snap,
                        "has_real_snapshot": False,
                        "data_status": "sample_available" if has_snap else "no_data"
                    }
                    families.append(family_summary)
                return families
        return []

    def resolve_family_id(self, market_id: str, product_id: str, family_id: str) -> str:
        families = self.list_families_by_product(market_id, product_id)
        for f in families:
            if f["family_id"] == family_id or f["safe_id"] == family_id:
                return f["family_id"]
        return family_id

    def get_family(self, market_id: str, product_id: str, family_id: str):
        m_id_canonical = self.resolve_market_id(market_id)
        p_id_canonical = self.resolve_product_id(m_id_canonical, product_id)
        f_id_canonical = self.resolve_family_id(m_id_canonical, p_id_canonical, family_id)
        
        families = self.list_families_by_product(m_id_canonical, p_id_canonical)
        for f in families:
            if f.get("family_id") == f_id_canonical:
                return f
        return None

    def validate_market_product_family(self, market_id: str, product_id: str, family_id: str) -> bool:
        family = self.get_family(market_id, product_id, family_id)
        return family is not None
