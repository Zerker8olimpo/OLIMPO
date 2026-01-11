# core/errors.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class OlimpoError(Exception):
    code: str
    message: str
    status: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        base = f"[{self.code}] {self.message}"
        if self.status is not None:
            base += f" (HTTP {self.status})"
        return base


def from_http(status: int, payload: Optional[Dict[str, Any]] = None) -> OlimpoError:
    """
    Crea un error estándar desde un HTTP status + payload JSON.
    Intenta extraer 'detail' o 'message' del backend si existe.
    """
    msg = "Error desconocido"
    if isinstance(payload, dict):
        msg = (
            str(payload.get("detail"))
            if payload.get("detail") is not None
            else str(payload.get("message", msg))
        )

    if status == 401:
        return OlimpoError(code="AUTH_EXPIRED", message=msg, status=status, details=payload)
    if status == 403:
        return OlimpoError(code="FORBIDDEN", message=msg, status=status, details=payload)
    if status == 423:
        return OlimpoError(code="DEVICE_BLOCKED", message=msg, status=status, details=payload)
    if status == 402:
        return OlimpoError(code="SUBSCRIPTION_REQUIRED", message=msg, status=status, details=payload)

    return OlimpoError(code="HTTP_ERROR", message=msg, status=status, details=payload)
