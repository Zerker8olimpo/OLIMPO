from pydantic import BaseModel
from typing import Optional, Literal

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    detail: Optional[dict] = None

class OkResponse(BaseModel):
    status: Literal["ok"] = "ok"