"""
Shim de compatibilidad para imports legacy.

Ruta oficial del Observatorio:
    backend.observatory.services.observatory_service

Este módulo existe solo para evitar rupturas en imports heredados mientras se
termina el saneamiento del dominio OSEngine.
"""

from backend.observatory.services.observatory_service import (  # noqa: F401
    ObservatoryService,
    observatory_service,
)
