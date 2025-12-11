from pydantic import BaseModel, Field
from typing import List


class PoseidonInput(BaseModel):
    """
    Entrada oficial del módulo POSEIDÓN (doble tanque + Kalman + DT).
    """
    product_id: str = Field(..., description="ID del producto.")
    market_id: str = Field(..., description="Mercado asociado.")

    inventario_observado: List[float] = Field(
        ..., description="Serie temporal del inventario observado."
    )

    horizonte_meses: int = Field(
        3, ge=1, le=36, description="Meses para proyectar el comportamiento del inventario."
    )

    # Parámetros opcionales (si tu versión final de process_poseidon los usa)
    Q: float = Field(1.0, ge=0, description="Varianza del proceso (Kalman).")
    R: float = Field(1.0, ge=0, description="Varianza de observación (Kalman).")


class PoseidonOutput(BaseModel):
    """
    Salida oficial del módulo POSEIDÓN.
    """
    product_id: str
    market_id: str
    horizonte_meses: int

    inventario_filtrado: List[float]
    flujo_entrada: List[float]
    flujo_salida: List[float]
    inventario_proyectado: List[float]

    phi_series: List[float]
    g_series: List[float]
    shock_index: List[float]

    psi: float
    params_dt: dict

    metadata: dict