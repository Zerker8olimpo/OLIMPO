# backend/core/device_control.py
from backend.database.device_store import (
    get_device_by_user,
    register_device,
    touch_device
)
from backend.database.device_conflict_store import log_conflict
from backend.core.errors import DeviceConflictError


def validate_device(user_id: int, device_uuid: str, platform: str, ip_address: str):
    record = get_device_by_user(user_id)

    if record is None:
        register_device(user_id, device_uuid, platform)
        return

    if record["device_uuid"] == device_uuid:
        touch_device(record["id"])
        return

    log_conflict(user_id, device_uuid, ip_address)
    raise DeviceConflictError()
