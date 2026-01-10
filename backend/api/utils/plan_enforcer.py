# backend/api/utils/plan_enforcer.py
from fastapi import HTTPException

PLAN_ORDER = {"none": 0, "basic": 1, "pro": 2, "enterprise": 3}

MODEL_MIN_PLAN = {
    "epsilon": "basic",
    "sigma": "pro",
    "poseidon": "enterprise",
}

def enforce_plan(plan: str, model: str):
    required = MODEL_MIN_PLAN.get(model, "enterprise")
    if PLAN_ORDER.get(plan, 0) < PLAN_ORDER[required]:
        raise HTTPException(status_code=403, detail="PLAN_NOT_ALLOWED")
