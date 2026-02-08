from typing import Dict, List

PLAN_BASIC = "olimpo_basic_monthly"
PLAN_PRO = "olimpo_pro_monthly"
PLAN_ENTERPRISE = "olimpo_enterprise_monthly"

PLAN_ALIAS = {
    PLAN_BASIC: "basic",
    PLAN_PRO: "pro",
    PLAN_ENTERPRISE: "enterprise",
}

PLAN_MODEL_MAP: Dict[str, List[str]] = {
    "basic": ["epsilon"],
    "pro": ["epsilon", "sigma"],
    "enterprise": ["epsilon", "sigma", "poseidon"],
}

def normalize_plan(google_product_id: str) -> str:
    """
    Convierte el ID de producto de Google Play (ej: olimpo_pro_monthly)
    al ID interno del plan (ej: pro).
    Si no coincide, retorna 'basic' por defecto.
    """
    return PLAN_ALIAS.get(google_product_id, "basic")

# ------------------------------------------------------------------
# ADAPTADOR DE COMPATIBILIDAD LEGACY
# ------------------------------------------------------------------
# IMPORTANTE:
# - NO usar PLANS para nueva lógica
# - Mantener solo para routers legacy y compatibilidad
# - La fuente de verdad moderna sigue siendo:
#   PLAN_MODEL_MAP y normalize_plan()
# ------------------------------------------------------------------

PLANS = {
    "basic": {
        "id": "basic",
        "price": 19990,
        "title": "OLIMPO Basic",
        "models_enabled": PLAN_MODEL_MAP["basic"],
    },
    "pro": {
        "id": "pro",
        "price": 29990,
        "title": "OLIMPO Pro",
        "models_enabled": PLAN_MODEL_MAP["pro"],
    },
    "enterprise": {
        "id": "enterprise",
        "price": 39990,
        "title": "OLIMPO Enterprise",
        "models_enabled": PLAN_MODEL_MAP["enterprise"],
    },
}