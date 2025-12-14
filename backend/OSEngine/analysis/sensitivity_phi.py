import statistics
from typing import List, Dict, Any, Optional


# ============================================================
# SensitivityPhi v2.0
# Correlación dinámica Producto ↔ Mercado | Determinístico
# ============================================================

def compute_phi(
    product_series: List[float],
    market_series: List[float],
    cfg: Dict[str, Any],
    trend_result: Optional[Dict[str, Any]] = None,
    volatility_result: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calcula la sensibilidad φ entre producto y mercado.
    """

    min_len = cfg["general"]["min_length"]
    if (
        not product_series
        or not market_series
        or len(product_series) < min_len
        or len(market_series) < min_len
    ):
        return _empty_result(context)

    # Alinear longitudes (últimos N puntos comunes)
    n = min(len(product_series), len(market_series))
    p = product_series[-n:]
    m = market_series[-n:]

    # --------------------------------------------------------
    # 1. Correlación short y long
    # --------------------------------------------------------
    phi_short = _rolling_corr(
        p, m, cfg["windows"]["short"]
    )

    phi_long = _rolling_corr(
        p, m, cfg["windows"]["long"]
    )

    # --------------------------------------------------------
    # 2. Valor φ combinado
    # --------------------------------------------------------
    w = cfg["weights"]
    phi_value = (
        w["short"] * abs(phi_short) +
        w["long"] * abs(phi_long)
    )

    phi_value = min(phi_value, cfg["limits"]["max_phi"])

    # --------------------------------------------------------
    # 3. Estabilidad de φ
    # --------------------------------------------------------
    stability = _phi_stability(
        p, m, cfg
    )

    # --------------------------------------------------------
    # 4. Ajustes contextuales (sin decidir)
    # --------------------------------------------------------
    # Si hay alta volatilidad, degradamos confianza
    confidence = _confidence_phi(
        stability=stability,
        volatility_result=volatility_result,
        cfg=cfg
    )

    return {
        "phi": {
            "value": round(phi_value, 4),
            "short": round(phi_short, 4),
            "long": round(phi_long, 4),
            "stability": round(stability, 3),
            "confidence": round(confidence, 3)
        },
        "context": context or {}
    }


# ============================================================
# Internos
# ============================================================

def _rolling_corr(x: List[float], y: List[float], window: int) -> float:
    if len(x) < window or window < 2:
        return 0.0

    xs = x[-window:]
    ys = y[-window:]

    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)

    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(window))
    den_x = sum((xs[i] - mean_x) ** 2 for i in range(window))
    den_y = sum((ys[i] - mean_y) ** 2 for i in range(window))

    den = (den_x * den_y) ** 0.5 + 1e-12
    return num / den


def _phi_stability(p: List[float], m: List[float], cfg: Dict[str, Any]) -> float:
    """
    Estabilidad de φ: cuán consistente es la correlación en ventanas móviles.
    """
    w = cfg["windows"]["stability"]
    if len(p) < w * 2:
        return 0.0

    corrs = []
    for i in range(w, len(p)):
        corrs.append(_rolling_corr(p[:i], m[:i], w))

    if len(corrs) < 2:
        return 0.0

    std_corr = statistics.pstdev(corrs)
    max_std = cfg["stability"]["max_std"] + 1e-6

    # std baja → estabilidad alta
    return max(0.0, min(1.0, 1.0 - std_corr / max_std))


def _confidence_phi(stability: float, volatility_result, cfg: Dict[str, Any]) -> float:
    """
    Confianza baja si:
    - estabilidad baja
    - volatilidad total alta
    """
    conf = stability

    if volatility_result:
        sigma = volatility_result.get("sigma", {}).get("total", 0.0)
        sigma_ref = cfg["confidence"]["sigma_ref"]
        conf *= max(0.0, 1.0 - sigma / (sigma_ref + 1e-6))

    return max(0.0, min(conf, 1.0))


def _empty_result(context):
    return {
        "phi": {
            "value": 0.0,
            "short": 0.0,
            "long": 0.0,
            "stability": 0.0,
            "confidence": 0.0
        },
        "context": context or {}
    }
