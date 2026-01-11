# core/storage.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_json(path: str) -> Optional[Dict[str, Any]]:
    """
    Carga un JSON desde disco.
    Retorna None si no existe o si hay error de parseo.
    """
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path: str, data: Dict[str, Any]) -> None:
    """
    Guarda un dict como JSON en disco, creando carpetas si es necesario.
    """
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
