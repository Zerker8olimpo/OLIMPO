"""
POSEIDON_SERVICE.py
Servicio oficial del modelo POSEIDÓN para OLIMPO.
"""

from typing import Dict, Any

from backend.digital_twin.helios_engine import HeliosEngine


def run_poseidon_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta POSEIDÓN usando el motor HELIOS backend.
    """

    engine = HeliosEngine(enable_logs=False)

    result = engine.run_poseidon(input_data)

    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result
