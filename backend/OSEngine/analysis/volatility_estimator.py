import statistics
from typing import List, Dict, Any, Optional


# ============================================================
# VolatilityEstimator v2.5
# EWMA + Histórica + Shock-aware | Determinístico | ML-ready
# ============================================================

def estimate_volatility(
    product_series: List[float],
    cfg: Dict[str, Any],
    shock_result: Optional[Dict[str, Any]] = None,
    market_series: Optional[List[float]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Estima la volatilidad operativa del producto seleccionado,
    incorporando volatilidad reciente (EWMA), histórica y shocks.
    """

    if not product_series or len(product_series) < cfg["general"]["min_length"]:
        return _empty_result(context)

    # --------------------------------------------------------
    # 1. Volatilidad histórica
    # --------------------------------------------------------
    hist_sigma = _historical_volatility(product_series)

    # --------------------------------------------------------
    # 2. Volatilidad EWMA (reciente)
    # --------------------------------------------------------
    ewma_sigma = _ewma_volatility(
        product_series,
        cfg["ewma"]["lambda"]
    )

    # --------------------------------------------------------
    # 3. Volatilidad inducida por shock
    # --------------------------------------------------------
    shock_sigma = 0.0
    shock_intensity = 0.0

    if shock_result:
        shock_intensity = shock_result.get("product", {}).get("intensity", 0.0)
        shock_sigma = shock_intensity * cfg["shock"]["multiplier"]

    # --------------------------------------------------------
    # 4. Volatilidad de mercado (opcional)
    # --------------------------------------------------------
    market_sigma = 0.0
    if (
        market_series
        and cfg["market"]["enabled"]
        and len(market_series) >= cfg["general"]["min_length"]
    ):
        market_sigma = _historical_volatility(market_series)

    # --------------------------------------------------------
    # 5. Volatilidad total combinada
    # --------------------------------------------------------
    w = cfg["weights"]

    sigma_total = (
        w["historical"] * hist_sigma +
        w["ewma"] * ewma_sigma +
        w["shock"] * shock_sigma +
        w["market"] * market_sigma
    )

    sigma_total = max(sigma_total, 0.0)

    # --------------------------------------------------------
    # 6. Clasificación de riesgo
    # --------------------------------------------------------
    risk_band = _risk_band(sigma_total, cfg["risk_bands"])

    # --------------------------------------------------------
    # 7. Confianza de la estimación
    # --------------------------------------------------------
    confidence = _confidence_score(
        hist_sigma, ewma_sigma, shock_sigma, market_sigma
    )

    return {
        "sigma": {
            "historical": round(hist_sigma, 4),
            "ewma": round(ewma_sigma, 4),
            "shock": round(shock_sigma, 4),
            "market": round(market_sigma, 4),
            "total": round(sigma_total, 4)
        },
        "risk_band": risk_band,
        "confidence": round(confidence, 3),
        "context": context or {}
    }


# ============================================================
# Cálculos internos
# ============================================================

def _historical_volatility(series: List[float]) -> float:
    if len(series) < 2:
        return 0.0
    return statistics.pstdev(series)


def _ewma_volatility(series: List[float], lam: float) -> float:
    if len(series) < 2:
        return 0.0

    var = 0.0
    for i in range(1, len(series)):
        diff = series[i] - series[i - 1]
        var = lam * var + (1 - lam) * diff ** 2

    return var ** 0.5


def _risk_band(sigma: float, bands: Dict[str, float]) -> str:
    if sigma < bands["low"]:
        return "low"
    elif sigma < bands["medium"]:
        return "medium"
    else:
        return "high"


def _confidence_score(hist, ewma, shock, market):
    score = 0.0
    if hist > 0:
        score += 0.3
    if ewma > 0:
        score += 0.3
    if shock > 0:
        score += 0.2
    if market > 0:
        score += 0.2
    return min(score, 1.0)


def _empty_result(context):
    return {
        "sigma": {
            "historical": 0.0,
            "ewma": 0.0,
            "shock": 0.0,
            "market": 0.0,
            "total": 0.0
        },
        "risk_band": "low",
        "confidence": 0.0,
        "context": context or {}
    }
