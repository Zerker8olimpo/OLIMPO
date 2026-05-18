import json
import os
import logging

class CompatibilityAliasAdapter:
    def __init__(self, cfg_path: str = "backend/cfg/CFG_AGORA_ALIAS_MAP.json"):
        self.mapping = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.mapping = data.get("legacy_to_canonical", {})

    def resolve_market_alias(self, market: str) -> str:
        markets = self.mapping.get("markets", {})
        if market in markets:
            return markets[market]["canonical_market_id"]
        return market

    def resolve_product_alias(self, product: str) -> str:
        products = self.mapping.get("products", {})
        if product in products:
            return products[product]["canonical_product_id"]
        return product

    def resolve_subfamily_alias(self, subfamily: str) -> str:
        subfamilies = self.mapping.get("subfamilies", {})
        if subfamily in subfamilies:
            return subfamilies[subfamily]["canonical_family_id"]
        return subfamily

    def resolve_legacy_to_canonical(self, market: str, product: str, subfamily: str):
        subfamilies = self.mapping.get("subfamilies", {})
        if subfamily in subfamilies:
            mapped_sub = subfamilies[subfamily]
            return mapped_sub["canonical_market_id"], mapped_sub["canonical_product_id"], mapped_sub["canonical_family_id"]
        
        # Fallback partial resolution
        return self.resolve_market_alias(market), self.resolve_product_alias(product), self.resolve_subfamily_alias(subfamily)
