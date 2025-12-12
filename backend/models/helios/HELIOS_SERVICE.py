"""
HELIOS_SERVICE.py
Servicio oficial del DIGITAL TWIN (HELIOS)
"""

from typing import Dict, Any

from backend.digital_twin.helios_engine import HeliosEngine


def run_helios_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta el Digital Twin completo (HELIOS)
    """

    engine = HeliosEngine(enable_logs=False)

    result = engine.run_full(input_data)

    return result