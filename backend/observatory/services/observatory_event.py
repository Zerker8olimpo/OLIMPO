"""
Shim de compatibilidad para el modelo observacional.

Modelo canónico:
    backend.database.models.observatory_event.ObservatoryEvent

Este módulo se mantiene solo para evitar rupturas en imports heredados.
"""

from backend.database.models.observatory_event import ObservatoryEvent  # noqa: F401
