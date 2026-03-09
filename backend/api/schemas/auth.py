# backend/api/schemas/auth.py
from __future__ import annotations

from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=10)
    device_id: str = Field(..., min_length=3)
    platform: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"