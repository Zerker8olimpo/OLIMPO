"""
EPSILON_SERVICE.py
Servicio oficial de EPSILON para el backend OLIMPO.

Esta capa actúa como "puente" entre:
- La API (FastAPI)
- El motor HELIOS (Digital Twin)
- El modelo EPSILON

NO usa archivos ENTRADA/ ni PREDICCION/.
Recibe los datos desde la API en formato JSON
y ejecuta SOLO el bloque EPSILON usando:
    engine.run_epsilon(input_data)
"""

from typing import Dict, Any
from pathlib import Path

# Importación correcta del motor Digital Twin backend
from digital_twin.helios_engine import HeliosEngine


def run_epsilon_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta EPSILON usando HELIOS Digital Twin (Fase 1 backend).

    Parámetros:
        input_data (dict): JSON recibido por la API.

    Retorna:
        dict: Resultado unificado EPSILON + Digital Twin.
              Compatible con el schema EpsilonOutput.
    """

    # Crear instancia del motor HELIOS (sin logs para API)
    engine = HeliosEngine(enable_logs=False)

    # EPSILON recibe el input de la API (sin archivos)
    result = engine.run_epsilon(input_data)

    # result viene en formato: 
    # { "productos": [ { ... data ... } ] }

    # Para la API devolvemos directamente el dict interno.
    if "productos" in result and len(result["productos"]) > 0:
        return result["productos"][0]

    return result  # fallback en caso de tener estructura distinta
