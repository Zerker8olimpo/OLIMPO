"""
Compatibilidad legacy para imports históricos.

NO contiene implementación propia.
Reexporta la fachada oficial del observatorio desde:
backend.observatory.services.observatory_service
"""

from backend.observatory.services.observatory_service import (  # noqa: F401
    ObservatoryService,
    observatory_service,
)
