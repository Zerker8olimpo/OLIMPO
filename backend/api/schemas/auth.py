from pydantic import BaseModel


class GoogleAuthRequest(BaseModel):
    id_token: str
    device_id: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"