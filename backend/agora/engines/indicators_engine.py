from typing import Any, Dict, Optional

from backend.core.economic_indicators_client import EconomicIndicatorsClient

IMPACT_THRESHOLD_MEDIO = 0.02
IMPACT_THRESHOLD_ALTO = 0.05
DIRECTION_EPSILON = 0.005


def _classify_impact(abs_value: float) -> str:
    if abs_value >= IMPACT_THRESHOLD_ALTO:
        return "alto"
    if abs_value >= IMPACT_THRESHOLD_MEDIO:
        return "medio"
    return "bajo"


def _classify_direction(signed_pressure: float) -> str:
    if signed_pressure > DIRECTION_EPSILON:
        return "presiona_alza"
    if signed_pressure < -DIRECTION_EPSILON:
        return "presiona_baja"
    return "estable"


class IndicatorsEngine:
    """
    Calcula el score de presión económica E (ec. 23 de la maqueta):
    E = Σ (peso_i × variación_6m_i × signo_sensibilidad_i)

    Usa mindicador.cl (vía EconomicIndicatorsClient) para los indicadores que
    tienen un `codigo_mindicador` configurado. Los que no lo tienen (p.ej.
    logística/combustible, que no tiene fuente gratuita real-time - ver
    CLAUDE.md sección 8.2) se declaran honestamente como "sin_dato_real".
    """

    def __init__(self, client: Optional[EconomicIndicatorsClient] = None):
        self.client = client or EconomicIndicatorsClient()

    async def process(self, snapshot_data: Dict[str, Any], indicators_cfg: Dict[str, Any]) -> Dict[str, Any]:
        indicators_cfg = indicators_cfg or {}
        fallback_indicators = (snapshot_data or {}).get("indicators", {}) or {}

        codes = {cfg.get("codigo_mindicador") for cfg in indicators_cfg.values() if cfg.get("codigo_mindicador")}
        results = await self.client.get_indicators(list(codes)) if codes else {}

        output: Dict[str, Any] = {}
        pressure_terms = []

        for name, cfg in indicators_cfg.items():
            codigo = cfg.get("codigo_mindicador")
            weight = cfg.get("weight", 0.0)
            direction_cfg = cfg.get("sensitivity_direction", "presiona_alza")
            sign = 1.0 if direction_cfg == "presiona_alza" else -1.0

            fetched = results.get(codigo) if codigo else None
            variation = fetched.get("variacion_6m") if fetched else None

            if fetched and fetched.get("status") == "ok" and variation is not None:
                signed_pressure = weight * variation * sign
                output[name] = {
                    "variation_6m": round(variation, 4),
                    "impact": _classify_impact(abs(variation)),
                    "direction": _classify_direction(signed_pressure),
                }
                pressure_terms.append(signed_pressure)
            elif name in fallback_indicators:
                output[name] = fallback_indicators[name]
            else:
                output[name] = {"variation_6m": 0.0, "impact": "sin_dato_real", "direction": "sin_dato_real"}

        economic_pressure_value = sum(pressure_terms)
        output["economic_pressure_index"] = {
            "variation_6m": round(economic_pressure_value, 4),
            "impact": _classify_impact(abs(economic_pressure_value)),
            "direction": _classify_direction(economic_pressure_value),
        }

        return output
