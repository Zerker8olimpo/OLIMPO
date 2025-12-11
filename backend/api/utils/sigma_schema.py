from pydantic import BaseModel, Field
from typing import List


class SigmaInput(BaseModel):
    """
    Entrada oficial para el modelo SIGMA (EOQ + ROP + Digital Twin).
    """
    demanda_historica: List[float] = Field(
        ..., description="Demanda histórica mensual del producto."
    )
    product_id: str = Field(
        ..., description="ID del producto."
    )
    market_id: str = Field(
        ..., description="ID del mercado asociado."
    )

    horizonte_meses: int = Field(
        3, ge=1, le=36, description="Meses a proyectar."
    )
    periodos: int = Field(
        12, ge=1, le=24, description="Número de periodos anuales (EOQ)."
    )

    costo_unitario: float = Field(
        ..., ge=0, description="Costo unitario del producto."
    )
    costo_pedido: float = Field(
        ..., ge=0, description="Costo por pedido (S)."
    )
    costo_mantencion_pct: float = Field(
        ..., ge=0, le=1, description="Costo anual de mantener inventario (i)."
    )


class SigmaOutput(BaseModel):
    """
    Salida oficial del modelo SIGMA (EOQ + ROP + DT + Montecarlo).
    """
    product_id: str
    market_id: str
    horizonte_meses: int
    periodos_anuales: int

    costo_unitario: float
    costo_pedido: float
    costo_mantencion_pct: float

    demanda_historica: List[float]
    forecast_base: List[float]
    demanda_dt: List[float]
    p50: List[float]
    p95: List[float]

    eoq_base: List[float]
    eoq_dt: List[float]
    eoq_p50: List[float]
    eoq_p95: List[float]

    rop_base: List[float]
    rop_dt: List[float]
    rop_p50: List[float]
    rop_p95: List[float]

    shock_index: List[float]
    phi_series: List[float]
    g_series: List[float]

    psi: float
    params_dt: dict

    lead_time_meses: float
    nivel_servicio: float
