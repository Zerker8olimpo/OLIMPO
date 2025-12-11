"""
POSEIDON_SERVICE.py
Servicio oficial del modelo POSEIDÓN para OLIMPO.

Este archivo conecta:
- API (FastAPI)
- HeliosEngine (Digital Twin)
- Módulo Poseidón (doble tanque + Kalman)

No usa archivos ENTRADA/.
Recibe datos desde la API.
"""

from typing import Dict, Any
from digital_twin.helios_engine import HeliosEngine


def run_poseidon_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta solamente POSEIDÓN usando el motor HELIOS backend.
    """

    # Motor HELIOS sin logs (modo API)
    engine = HeliosEngine(enable_logs=False)

    # Pasar el input directo (sin archivos)
    result = engine.run_poseidon(input_data)

    # La salida real es:
    # { "productos": [ { ... } ] }
    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result