from pydantic import BaseModel, Field
from typing import Dict, Any


class HeliosInput(BaseModel):
    """
    Entrada oficial del Digital Twin completo HELIOS.
    La API recibe las tres entradas de los modelos por separado.
    """
    epsilon_input: Dict[str, Any] = Field(
        ..., description="Input del modelo EPSILON."
    )
    sigma_input: Dict[str, Any] = Field(
        ..., description="Input del modelo SIGMA."
    )
    poseidon_input: Dict[str, Any] = Field(
        ..., description="Input del modelo POSEIDÓN."
    )

    write_output: bool = Field(
        False,
        description="Si True, escribe el archivo PREDICCION_DT.json en backend/prediccion/."
    )


class HeliosOutput(BaseModel):
    """
    Salida oficial del Digital Twin completo.
    """
    HELIOS_DIGITALTWIN: Dict[str, Any]