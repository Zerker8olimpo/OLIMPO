from pydantic import BaseModel
from typing import Optional, List


class BootstrapUser(BaseModel):
    id: str
    email: str
    display_name: str


class BootstrapSubscription(BaseModel):
    status: str
    plan_id: Optional[str]
    has_active_plan: bool
    models_enabled: List[str]


class BootstrapLimits(BaseModel):
    max_runs_per_day: int
    max_horizon: int


class BootstrapResponse(BaseModel):
    user: Optional[BootstrapUser]
    subscription: BootstrapSubscription
    limits: BootstrapLimits