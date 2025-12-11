"""
HELIOS_SERVICE.py
Servicio oficial del Digital Twin completo para OLIMPO.

Conecta:
- FastAPI
- HeliosEngine (Digital Twin)
- Los tres modelos: Epsilon, Sigma, Poseidón

No usa ENTRADA/. Recibe todo desde la API.
"""

from typing import Dict, Any
from digital_twin.helios_engine import HeliosEngine


def run_helios_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta el Digital Twin completo (Epsilon + Sigma + Poseidón)
    utilizando el motor HELIOS en su modo backend.
    """

    engine = HeliosEngine(enable_logs=False)

    epsilon_input = input_data.get("epsilon_input", {})
    sigma_input = input_data.get("sigma_input", {})
    poseidon_input = input_data.get("poseidon_input", {})
    write_output = bool(input_data.get("write_output", False))

    result = engine.run_digital_twin(
        epsilon_input=epsilon_input,
        sigma_input=sigma_input,
        poseidon_input=poseidon_input,
        write_output=write_output
    )

    return result