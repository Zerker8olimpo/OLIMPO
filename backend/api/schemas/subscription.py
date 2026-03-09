# backend/api/schemas/subscription.py
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SubscriptionStatusResponse(BaseModel):
    planId: Optional[str] = None
    status: Literal["active", "no_plan"] = "no_plan"
    entitlements: List[str] = Field(default_factory=list)