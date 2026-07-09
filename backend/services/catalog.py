import json
from pathlib import Path
from functools import lru_cache
from typing import Optional
from fastapi import APIRouter, Query

router = APIRouter(prefix="/web/catalog", tags=["catalog"])

_CFG_PRODUCTOS_PATH = Path(__file__).resolve().parents[2] / "cfg" / "CFG_HELIOS_PRODUCTOS.json"


@lru_cache(maxsize=1)
def _load_productos() -> list:
    with _CFG_PRODUCTOS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f).get("productos", [])


@router.get("/markets")
def get_markets():
    seen = {}
    for p in _load_productos():
        mid = p.get("market_id")
        if mid and mid not in seen:
            seen[mid] = p.get("market_nombre", mid)
    return sorted(
        [{"market_id": k, "market_nombre": v} for k, v in seen.items()],
        key=lambda x: x["market_nombre"],
    )


@router.get("/products")
def get_products(market_id: Optional[str] = Query(None)):
    out = [
        {"product_id": p.get("product_id"), "product_nombre": p.get("product_nombre", p.get("product_id"))}
        for p in _load_productos()
        if market_id is None or p.get("market_id") == market_id
    ]
    return sorted(out, key=lambda x: x["product_nombre"])