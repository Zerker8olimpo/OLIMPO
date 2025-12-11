"""
SIGMA_SERVICE.py
Servicio oficial del modelo SIGMA para OLIMPO.

Conecta:
- FastAPI
- HeliosEngine (Digital Twin)
- Modelo SIGMA

No lee archivos ENTRADA/.
Recibe JSON desde la API y devuelve la salida limpia.
"""

from typing import Dict, Any

from digital_twin.helios_engine import HeliosEngine


def run_sigma_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta SIGMA usando el motor HELIOS en modo backend.
    """

    # Instancia del motor (sin logs, ideal para API)
    engine = HeliosEngine(enable_logs=False)

    # Ejecutar solo SIGMA
    result = engine.run_sigma(input_data)

    # La estructura devuelta por HELIOS es:
    # { "productos": [ { ... } ] }
    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result  # fallback