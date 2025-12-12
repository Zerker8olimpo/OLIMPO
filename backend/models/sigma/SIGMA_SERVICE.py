"""
SIGMA_SERVICE.py
Servicio oficial del modelo SIGMA para OLIMPO.
"""

from typing import Dict, Any

from backend.digital_twin.helios_engine import HeliosEngine


def run_sigma_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta SIGMA usando el motor HELIOS backend.
    """

    engine = HeliosEngine(enable_logs=False)

    result = engine.run_sigma(input_data)

    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result
