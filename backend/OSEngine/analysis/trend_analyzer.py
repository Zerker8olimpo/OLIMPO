import statistics
from typing import List, Dict, Any, Optional


# ============================================================
# TrendAnalyzer v2.0
# Regresión rolling + Clasificación | Determinístico | ML-ready
# ============================================================

def analyze_trend(
    product_series: List[float],
    cfg: Dict[str, Any],
    shock_result: Optional[Dict[str, Any]] = None,
    volatility_result: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    if not product_series or len(product_series) < cfg["general"]["min_length"]:
        return _empty_result(context)

    window = cfg["regression"]["window"]
    if len(product_series) < window:
        window = len(product_series)

    y = product_series[-window:]
    slope = _rolling_slope(y)

    # Normalización suave de slope para comparar contra umbrales
    slope_norm = slope / (statistics.pstdev(y) + 1e-6)

    # Señales auxiliares
    shock_intensity = 0.0
    if shock_result:
        shock_intensity = shock_result.get("product", {}).get("intensity", 0.0)

    sigma_total = 0.0
    if volatility_result:
        sigma_total = volatility_result.get("sigma", {}).get("total", 0.0)

    direction = _classify_direction(
        slope_norm,
        cfg["thresholds"]["up"],
        cfg["thresholds"]["down"]
    )

    # Si hay shock alto, degradamos la confianza en tendencia
    confidence = _confidence(
        y=y,
        slope_norm=slope_norm,
        sigma_total=sigma_total,
        shock_intensity=shock_intensity,
        cfg=cfg
    )

    stability = _stability_score(y, cfg["stability"])

    # Si el sistema está muy volátil, puede volverse "chaotic"
    if sigma_total >= cfg["chaos"]["sigma_threshold"] and shock_intensity >= cfg["chaos"]["shock_threshold"]:
        direction = "chaotic"

    return {
        "trend": {
            "direction": direction,
            "slope": round(slope, 6),
            "slope_norm": round(slope_norm, 4),
            "confidence": round(confidence, 3),
            "stability": round(stability, 3)
        },
        "context": context or {}
    }


# ============================================================
# Internos
# ============================================================

def _rolling_slope(y: List[float]) -> float:
    """
    Pendiente OLS simple para y vs t (t=0..n-1)
    """
    n = len(y)
    if n < 2:
        return 0.0

    t = list(range(n))
    mean_t = (n - 1) / 2.0
    mean_y = statistics.fmean(y)

    num = sum((t[i] - mean_t) * (y[i] - mean_y) for i in range(n))
    den = sum((t[i] - mean_t) ** 2 for i in range(n)) + 1e-12

    return num / den


def _classify_direction(slope_norm: float, up_thr: float, down_thr: float) -> str:
    if slope_norm >= up_thr:
        return "up"
    if slope_norm <= -down_thr:
        return "down"
    return "flat"


def _confidence(y, slope_norm, sigma_total, shock_intensity, cfg):
    """
    Confianza baja si:
    - pocos datos efectivos
    - volatilidad total alta
    - shock alto (posible distorsión temporal)
    """
    n = len(y)
    base = min(1.0, n / cfg["confidence"]["full_window"])

    # Penalizaciones
    penalty_vol = min(1.0, sigma_total / (cfg["confidence"]["sigma_ref"] + 1e-6))
    penalty_shock = shock_intensity

    # Magnitud de tendencia ayuda a confianza
    trend_boost = min(1.0, abs(slope_norm) / (cfg["confidence"]["slope_ref"] + 1e-6))

    conf = (
        cfg["confidence"]["w_base"] * base +
        cfg["confidence"]["w_trend"] * trend_boost -
        cfg["confidence"]["w_vol"] * penalty_vol -
        cfg["confidence"]["w_shock"] * penalty_shock
    )

    return max(0.0, min(conf, 1.0))


def _stability_score(y: List[float], s_cfg: Dict[str, Any]) -> float:
    """
    Estabilidad: 1 si variación relativa baja, 0 si muy errática.
    """
    if len(y) < 2:
        return 0.0

    std = statistics.pstdev(y)
    mean = abs(statistics.fmean(y)) + 1e-6
    cv = std / mean  # coeficiente de variación

    # Normalizar CV a [0,1] invertido
    # cv <= cv_low  -> estabilidad ~1
    # cv >= cv_high -> estabilidad ~0
    if cv <= s_cfg["cv_low"]:
        return 1.0
    if cv >= s_cfg["cv_high"]:
        return 0.0

    return 1.0 - (cv - s_cfg["cv_low"]) / (s_cfg["cv_high"] - s_cfg["cv_low"])


def _empty_result(context):
    return {
        "trend": {
            "direction": "flat",
            "slope": 0.0,
            "slope_norm": 0.0,
            "confidence": 0.0,
            "stability": 0.0
        },
        "context": context or {}
    }