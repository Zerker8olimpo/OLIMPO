from pydantic import BaseModel, Field
from typing import List


class EpsilonInput(BaseModel):
    """
    Schema de entrada para el modelo EPSILON.
    Este esquema es el que recibirá la API desde la app móvil.
    """
    demanda_historica: List[float] = Field(
        ..., description="Demanda mensual histórica utilizada como base del forecast."
    )
    product_id: str = Field(
        ..., description="ID del producto seleccionado por el usuario."
    )
    market_id: str = Field(
        ..., description="ID del mercado seleccionado por el usuario."
    )
    horizonte_meses: int = Field(
        ..., ge=1, le=36,
        description="Cantidad de meses a proyectar en el forecast."
    )
    margen_bruto_pct: float = Field(
        0.3, ge=0, le=1,
        description="Factor alfa para SES, basado en margen bruto o sensibilidad."
    )


class EpsilonOutput(BaseModel):
    """
    Schema de salida del modelo EPSILON.
    Esta estructura será devuelta a la app móvil.
    """
    product_id: str
    market_id: str
    horizonte_meses: int

    # Forecast base SES
    forecast_base: List[float]

    # Forecast ajustado por el Digital Twin (phi–Phi–Psi)
    forecast_dt: List[float]

    # Resultados de Montecarlo (p50, p95)
    p50: List[float]
    p95: List[float]

    # Compra sugerida según nivel de servicio configurado
    compra_sugerida: List[float]

    # Series internas útiles para visualización en la app
    shock_index: List[float]
    phi_series: List[float]
    g_series: List[float]

    # Parámetro SES usado
    alpha_ses: float
