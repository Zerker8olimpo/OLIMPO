# core/device.py
from __future__ import annotations

import uuid
from typing import Optional

from core.storage import load_json, save_json

DEVICE_FILE = "data/device.json"


def get_or_create_device_id() -> str:
    """
    Retorna un device_id estable.
    Si no existe en data/device.json, crea uno y lo persiste.
    """
    data = load_json(DEVICE_FILE)
    if data and isinstance(data.get("device_id"), str) and data["device_id"].strip():
        return data["device_id"].strip()

    device_id = str(uuid.uuid4())
    save_json(DEVICE_FILE, {"device_id": device_id})
    return device_id
