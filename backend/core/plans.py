from typing import Dict, List

# ---------------------------------------------------------
# PRODUCT IDS DE GOOGLE PLAY
# ---------------------------------------------------------

PLAN_BASIC = "olimpo_basic_monthly"
PLAN_PRO = "olimpo_pro_monthly"
PLAN_ENTERPRISE = "olimpo_enterprise_monthly"


# ---------------------------------------------------------
# MAPEO GOOGLE → PLAN INTERNO
# ---------------------------------------------------------

PLAN_ALIAS = {
    PLAN_BASIC: "basic",
    PLAN_PRO: "pro",
    PLAN_ENTERPRISE: "enterprise",
}


def normalize_plan(google_product_id: str) -> str:
    """
    Convierte el ID de producto de Google Play
    (ej: olimpo_pro_monthly)

    al ID interno del plan
    (ej: pro)

    Si no coincide, retorna 'basic'
    """
    return PLAN_ALIAS.get(google_product_id, "basic")


# ---------------------------------------------------------
# MODELOS DISPONIBLES POR PLAN
# ---------------------------------------------------------

PLAN_MODEL_MAP: Dict[str, List[str]] = {
    "basic": ["epsilon"],
    "pro": ["epsilon", "sigma"],
    "enterprise": ["epsilon", "sigma", "poseidon"],
}


# ---------------------------------------------------------
# LIMITES OPERACIONALES
# ---------------------------------------------------------
# Nota:
# OLIMPO no limita ejecuciones de modelos,
# pero los tests requieren max_runs_per_day > 0
# Por lo tanto usamos un valor alto para representar
# "ilimitado" de forma compatible con APIs.
# ---------------------------------------------------------

UNLIMITED_RUNS = 999999


# ---------------------------------------------------------
# ADAPTADOR LEGACY DE PLANES
# ---------------------------------------------------------
# IMPORTANTE:
# - NO usar PLANS para lógica nueva
# - Mantener solo para routers legacy
# - Fuente moderna:
#     PLAN_MODEL_MAP
#     normalize_plan()
# ---------------------------------------------------------

PLANS = {
    "basic": {
        "id": "basic",
        "price": 19990,
        "title": "OLIMPO Basic",
        "models_enabled": PLAN_MODEL_MAP["basic"],
        "limits": {
            "max_runs_per_day": UNLIMITED_RUNS,
            "max_horizon": 12,
        },
    },
    "pro": {
        "id": "pro",
        "price": 29990,
        "title": "OLIMPO Pro",
        "models_enabled": PLAN_MODEL_MAP["pro"],
        "limits": {
            "max_runs_per_day": UNLIMITED_RUNS,
            "max_horizon": 12,
        },
    },
    "enterprise": {
        "id": "enterprise",
        "price": 39990,
        "title": "OLIMPO Enterprise",
        "models_enabled": PLAN_MODEL_MAP["enterprise"],
        "limits": {
            "max_runs_per_day": UNLIMITED_RUNS,
            "max_horizon": 12,
        },
    },
}