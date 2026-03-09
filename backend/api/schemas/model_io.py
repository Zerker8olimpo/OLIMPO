from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ===============================
# INTERPRETATION / WARNINGS
# ===============================

class Interpretation(BaseModel):
    summary: Optional[str] = None
    risk: Optional[str] = None
    confidence: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class WarningMessage(BaseModel):
    code: str = "MODEL_WARNING"
    message: str
    field: Optional[str] = None
    severity: str = "warning"


# ===============================
# EPSILON OUTPUT
# ===============================

class EpsilonOutput(BaseModel):

    # Series frontend
    expected: List[float] = Field(default_factory=list)
    smooth: List[float] = Field(default_factory=list)
    stress: List[float] = Field(default_factory=list)
    upper: List[float] = Field(default_factory=list)

    # Retrocompatibilidad
    p50: List[float] = Field(default_factory=list)
    p95: List[float] = Field(default_factory=list)

    # Series internas útiles
    forecast_base: List[float] = Field(default_factory=list)
    forecast_dt: List[float] = Field(default_factory=list)
    shock_index: List[float] = Field(default_factory=list)
    phi_series: List[float] = Field(default_factory=list)
    g_series: List[float] = Field(default_factory=list)

    # Metadata
    product_id: Optional[str] = None
    market_id: Optional[str] = None
    horizonte_meses: int = 0
    alpha_ses: float = 0.0

    # Resultados principales
    recommendedPurchase: float = 0.0
    compra_sugerida: List[float] = Field(default_factory=list)

    volatilityIndex: float = 0.0
    confidenceIndex: float = 0.0
    stability: float = 0.0


# ===============================
# SIGMA OUTPUT
# ===============================

class SigmaOutput(BaseModel):

    # Series frontend
    demandDt: List[float] = Field(default_factory=list)
    eoqDt: List[float] = Field(default_factory=list)
    ropDt: List[float] = Field(default_factory=list)

    # Series internas
    demanda_historica: List[float] = Field(default_factory=list)
    forecast_base: List[float] = Field(default_factory=list)
    demanda_dt: List[float] = Field(default_factory=list)

    p50: List[float] = Field(default_factory=list)
    p95: List[float] = Field(default_factory=list)

    eoq_base: List[float] = Field(default_factory=list)
    eoq_dt: List[float] = Field(default_factory=list)
    eoq_p50: List[float] = Field(default_factory=list)
    eoq_p95: List[float] = Field(default_factory=list)

    rop_base: List[float] = Field(default_factory=list)
    rop_dt: List[float] = Field(default_factory=list)
    rop_p50: List[float] = Field(default_factory=list)
    rop_p95: List[float] = Field(default_factory=list)

    shock_index: List[float] = Field(default_factory=list)
    phi_series: List[float] = Field(default_factory=list)
    g_series: List[float] = Field(default_factory=list)

    # Metadata
    product_id: Optional[str] = None
    market_id: Optional[str] = None
    horizonte_meses: int = 0

    periodos_anuales: int = 0

    costo_unitario: float = 0.0
    costo_pedido: float = 0.0
    costo_mantencion_pct: float = 0.0

    leadTimeMeses: float = 0.0
    nivelServicio: float = 0.0

    lead_time_meses: float = 0.0
    nivel_servicio: float = 0.0

    psi: float = 0.0

    params_dt: Dict[str, float] = Field(default_factory=dict)


# ===============================
# POSEIDON OUTPUT
# ===============================

class PoseidonNestedOutput(BaseModel):

    poseidonInventario1: List[float] = Field(default_factory=list)
    poseidonInventario2: List[float] = Field(default_factory=list)
    poseidonFlujo: List[float] = Field(default_factory=list)

    # Metadata
    product_id: Optional[str] = None
    market_id: Optional[str] = None
    horizonte_meses: int = 0

    # Series internas
    demanda_proyectada: List[float] = Field(default_factory=list)

    inventario_tanque1: List[float] = Field(default_factory=list)
    inventario_tanque2: List[float] = Field(default_factory=list)

    flujo_t1_t2: List[float] = Field(default_factory=list)
    produccion_sugerida: List[float] = Field(default_factory=list)

    pid_params: Dict[str, float] = Field(default_factory=dict)
    kalman_params: Dict[str, Any] = Field(default_factory=dict)


class PoseidonOutput(BaseModel):
    poseidon: PoseidonNestedOutput


# ===============================
# RESPONSE CONTRACT
# ===============================

class ModelRunResponse(BaseModel):

    modelName: str
    horizon: int = 0

    interpretation: Optional[Interpretation] = None

    warnings: List[WarningMessage] = Field(default_factory=list)

    modelOutput: Dict[str, Any] = Field(default_factory=dict)


# ===============================
# REQUEST CONTRACT
# ===============================

class ModelRunRequest(BaseModel):

    modelName: Optional[str] = None
    modelParams: Dict[str, Any] = Field(default_factory=dict)
    device_id: Optional[str] = None