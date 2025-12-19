from pydantic import BaseModel, Field
from typing import Literal

class HeliosSimulateRequest(BaseModel):
    device_id: str = Field(..., min_length=6)
    model: Literal["epsilon", "sigma", "poseidon"]
    horizon_days: int = Field(..., ge=1, le=365)
    confidence: float = Field(..., ge=0.5, le=0.99)
