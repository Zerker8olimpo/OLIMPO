from typing import Dict, Any, Optional


# ============================================================
# ImpactPsi v2.0
# Shock + Volatilidad + Phi | Determinístico | ML-ready
# ============================================================

def compute_psi(
    shock_result: Dict[str, Any],
    volatility_result: Dict[str, Any],
    phi_result: Optional[Dict[str, Any]],
    trend_result: Optional[Dict[str, Any]],
    cfg: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calcula el impacto operativo agregado ψ del entorno actual.
    """

    # --------------------------------------------------------
    # 1. Extraer señales base (con degradación segura)
    # --------------------------------------------------------
    shock_intensity = shock_result.get("product", {}).get("intensity", 0.0)
    shock_relative = shock_result.get("relative_shock", 0.0)

    sigma_total = volatility_result.get("sigma", {}).get("total", 0.0)

    phi_value = 0.0
    phi_conf = 0.0
    if phi_result:
        phi_value = phi_result.get("phi", {}).get("value", 0.0)
        phi_conf = phi_result.get("phi", {}).get("confidence", 0.0)

    trend_conf = 0.0
    if trend_result:
        trend_conf = trend_result.get("trend", {}).get("confidence", 0.0)

    # --------------------------------------------------------
    # 2. Impacto base ψ_raw
    # --------------------------------------------------------
    w = cfg["weights"]

    psi_raw = (
        w["shock"] * shock_intensity +
        w["volatility"] * sigma_total +
        w["phi"] * phi_value +
        w["relative"] * max(0.0, shock_relative)
    )

    psi_raw = min(psi_raw, cfg["limits"]["max_psi"])

    # --------------------------------------------------------
    # 3. Ajustes de coherencia (no decisiones)
    # --------------------------------------------------------
    # Si la tendencia es poco confiable, degradamos impacto efectivo
    psi_effective = psi_raw * (1.0 - cfg["penalties"]["trend"] * (1.0 - trend_conf))

    # --------------------------------------------------------
    # 4. Clasificación de impacto
    # --------------------------------------------------------
    impact_level = _impact_level(psi_effective, cfg["levels"])

    # --------------------------------------------------------
    # 5. Confianza del impacto
    # --------------------------------------------------------
    confidence = _psi_confidence(
        shock_conf=shock_result.get("confidence", 0.0),
        phi_conf=phi_conf,
        trend_conf=trend_conf,
        cfg=cfg
    )

    return {
        "psi": {
            "raw": round(psi_raw, 4),
            "effective": round(psi_effective, 4),
            "level": impact_level,
            "confidence": round(confidence, 3)
        },
        "context": context or {}
    }


# ============================================================
# Internos
# ============================================================

def _impact_level(psi: float, levels: Dict[str, float]) -> str:
    if psi < levels["minor"]:
        return "minor"
    if psi < levels["moderate"]:
        return "moderate"
    return "severe"


def _psi_confidence(shock_conf: float, phi_conf: float, trend_conf: float, cfg: Dict[str, Any]) -> float:
    w = cfg["confidence_weights"]
    conf = (
        w["shock"] * shock_conf +
        w["phi"] * phi_conf +
        w["trend"] * trend_conf
    )
    return max(0.0, min(conf, 1.0))
