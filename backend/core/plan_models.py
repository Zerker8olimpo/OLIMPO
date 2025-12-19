from enum import Enum
from typing import set

class Plan(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_MODELS: dict[Plan, set[str]] = {
    Plan.BASIC: {"epsilon"},
    Plan.PRO: {"epsilon", "sigma"},
    Plan.ENTERPRISE: {"epsilon", "sigma", "poseidon"},
}
