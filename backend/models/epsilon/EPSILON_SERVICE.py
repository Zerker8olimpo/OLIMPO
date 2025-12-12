"""
EPSILON_SERVICE.py
Servicio oficial del modelo EPSILON para OLIMPO.
"""

from typing import Dict, Any

from backend.digital_twin.helios_engine import HeliosEngine


def run_epsilon_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta EPSILON usando el Digital Twin (HeliosEngine)
    """

    engine = HeliosEngine(enable_logs=False)

    result = engine.run_epsilon(input_data)

    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result
