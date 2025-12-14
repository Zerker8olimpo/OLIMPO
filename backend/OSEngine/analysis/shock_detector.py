import statistics
from typing import List, Dict, Any, Optional


# ============================================================
# ShockDetector v2.5
# Producto + Mercado | Determinístico | ML-ready vía CFG
# ============================================================

def detect_shock(
    product_series: List[float],
    cfg: Dict[str, Any],
    market_series: Optional[List[float]] = None,
    context: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Detecta shocks relevantes en el producto seleccionado y,
    opcionalmente, en su mercado asociado.
    """

    if not product_series or len(product_series) < cfg["general"]["min_length"]:
        return _empty_result()

    # --------------------------------------------------------
    # Producto
    # --------------------------------------------------------
    prod_z_evt, prod_z = _zscore(product_series, cfg)
    prod_c_evt, prod_c_score, prod_state = _cusum(product_series, cfg, state)
    prod_b_evt, prod_b_score = _breakpoint(product_series, cfg)

    prod_intensity = _compute_intensity(
        prod_z, prod_c_score, prod_b_score, cfg
    )

    prod_type = _classify_shock(prod_z_evt, prod_c_evt, prod_b_evt, product_series)

    # --------------------------------------------------------
    # Mercado (opcional)
    # --------------------------------------------------------
    market_enabled = bool(
        market_series
        and cfg["market_analysis"]["enabled"]
        and len(market_series) >= cfg["general"]["min_length"]
    )

    market_intensity = 0.0
    market_type = "none"

    if market_enabled:
        m_z_evt, m_z = _zscore(market_series, cfg)
        m_c_evt, m_c_score, _ = _cusum(market_series, cfg, None)
        m_b_evt, m_b_score = _breakpoint(market_series, cfg)

        market_intensity = _compute_intensity(
            m_z, m_c_score, m_b_score, cfg
        )
        market_type = _classify_shock(m_z_evt, m_c_evt, m_b_evt, market_series)

    # --------------------------------------------------------
    # Shock relativo
    # --------------------------------------------------------
    relative_shock = prod_intensity - market_intensity

    # --------------------------------------------------------
    # Decisión final (detección, no control)
    # --------------------------------------------------------
    shock_flag = int(
        (prod_z_evt and prod_c_evt) or prod_b_evt
    )

    confidence = _compute_confidence(
        prod_z_evt, prod_c_evt, prod_b_evt, market_enabled
    )

    return {
        "shock_flag": shock_flag,
        "shock_type": prod_type,

        "product": {
            "intensity": round(prod_intensity, 3),
            "z_score": round(prod_z, 3),
            "cusum_score": round(prod_c_score, 3),
            "break_score": round(prod_b_score, 3)
        },

        "market": {
            "enabled": market_enabled,
            "intensity": round(market_intensity, 3),
            "shock_type": market_type
        },

        "relative_shock": round(relative_shock, 3),
        "confidence": round(confidence, 3),

        "state": prod_state,
        "context": context or {}
    }


# ============================================================
# Detectores internos
# ============================================================

def _zscore(series: List[float], cfg: Dict[str, Any]):
    z_cfg = cfg["z_score"]
    if not z_cfg["enabled"] or len(series) < z_cfg["window"]:
        return False, 0.0

    window = series[-z_cfg["window"]:]
    mean = statistics.fmean(window)
    std = statistics.pstdev(window) or 0.0

    if std == 0:
        return False, 0.0

    z = abs((series[-1] - mean) / std)
    return z >= z_cfg["threshold"], z


def _cusum(series: List[float], cfg: Dict[str, Any], state: Optional[Dict[str, float]]):
    c_cfg = cfg["cusum"]
    if not c_cfg["enabled"]:
        return False, 0.0, state or {"pos": 0.0, "neg": 0.0}

    if state is None:
        state = {"pos": 0.0, "neg": 0.0}

    mean = statistics.fmean(series)
    x = series[-1] - mean

    pos = max(0.0, state["pos"] + x - c_cfg["k"])
    neg = max(0.0, state["neg"] - x - c_cfg["k"])

    event = pos > c_cfg["h"] or neg > c_cfg["h"]
    score = min(max(pos, neg) / c_cfg["h"], 1.0)

    return event, score, {"pos": pos, "neg": neg}


def _breakpoint(series: List[float], cfg: Dict[str, Any]):
    b_cfg = cfg["breakpoint"]
    if not b_cfg["enabled"] or len(series) < 2 * b_cfg["window"]:
        return False, 0.0

    a = series[-2 * b_cfg["window"]:-b_cfg["window"]]
    b = series[-b_cfg["window"]:]

    mean_a = statistics.fmean(a)
    mean_b = statistics.fmean(b)

    std_a = statistics.pstdev(a) or 0.0
    std_b = statistics.pstdev(b) or 0.0

    pooled = max(std_a, std_b, 1e-6)
    score = abs(mean_b - mean_a) / pooled

    return score >= b_cfg["threshold"], min(score / b_cfg["threshold"], 1.0)


# ============================================================
# Utilidades
# ============================================================

def _compute_intensity(z, c, b, cfg):
    w = cfg["weights"]
    raw = w["z"] * z + w["cusum"] * c + w["break"] * b
    return min(raw, 1.0)


def _classify_shock(z_evt, c_evt, b_evt, series):
    if b_evt:
        return "regime_change"
    if z_evt and not c_evt:
        return "spike" if series[-1] > series[-2] else "drop"
    if c_evt:
        return "persistent_shift"
    return "none"


def _compute_confidence(z_evt, c_evt, b_evt, market_enabled):
    score = 0.0
    if z_evt:
        score += 0.3
    if c_evt:
        score += 0.4
    if b_evt:
        score += 0.3
    if market_enabled:
        score += 0.1
    return min(score, 1.0)


def _empty_result():
    return {
        "shock_flag": 0,
        "shock_type": "none",
        "product": {
            "intensity": 0.0,
            "z_score": 0.0,
            "cusum_score": 0.0,
            "break_score": 0.0
        },
        "market": {
            "enabled": False,
            "intensity": 0.0,
            "shock_type": "none"
        },
        "relative_shock": 0.0,
        "confidence": 0.0,
        "state": {"pos": 0.0, "neg": 0.0},
        "context": {}
    }
