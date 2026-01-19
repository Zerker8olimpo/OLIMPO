from datetime import timedelta

PLANS = {
    "basic": {
        "price": 19990,
        "currency": "CLP",
        "duration": timedelta(days=30),
        "models": ["epsilon"],
    },
    "pro": {
        "price": 29990,
        "currency": "CLP",
        "duration": timedelta(days=30),
        "models": ["epsilon", "sigma"],
    },
    "enterprise": {
        "price": 39990,
        "currency": "CLP",
        "duration": timedelta(days=30),
        "models": ["epsilon", "sigma", "poseidon"],
    },
}

def resolve_plan_by_amount(amount: float) -> str | None:
    for plan_name, cfg in PLANS.items():
        if cfg["price"] == amount:
            return plan_name
    return None