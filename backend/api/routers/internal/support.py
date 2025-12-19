# backend/api/routers/internal/support.py
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.database.device_store import delete_devices_by_user

router = APIRouter(prefix="/internal/support", tags=["internal"])
INTERNAL_TOKEN = os.getenv("INTERNAL_SUPPORT_TOKEN")


class ResetDeviceRequest(BaseModel):
    user_id: int


@router.post("/reset-device")
def reset_device(data: ResetDeviceRequest, request: Request):
    if request.headers.get("X-INTERNAL-TOKEN") != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    delete_devices_by_user(data.user_id)

    return {"status": "OK", "message": "Dispositivo reiniciado"}