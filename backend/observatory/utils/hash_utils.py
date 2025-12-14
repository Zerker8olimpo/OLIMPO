"""
Hash Utils
----------

Utilidades de anonimización / hashing para el Observatorio.
No contiene PII. Solo transforma identificadores en hashes.
"""

import hashlib
import hmac
from typing import Optional


def stable_hash(value: str, *, salt: str = "") -> str:
    """
    Hash estable (no reversible) para IDs.
    """
    data = (salt + value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def stable_hmac(value: str, *, secret: str) -> str:
    """
    HMAC-SHA256 (recomendado si hay secret del servidor).
    """
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_user_hash(user_id: str, *, secret: Optional[str] = None, salt: str = "olympo") -> str:
    """
    Devuelve hash de usuario sin exponer el ID real.
    Si hay secret, usa HMAC; si no, usa SHA256 con salt.
    """
    if secret:
        return stable_hmac(user_id, secret=secret)
    return stable_hash(user_id, salt=salt)
