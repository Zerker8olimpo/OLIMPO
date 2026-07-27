from typing import Any, Dict, Optional


class MarketForcesEngine:
    """
    Expone oferta/demanda (OD, ec. 24) y sustitutos (SUB, ec. 25) de la maqueta.

    No existe hoy una fuente real observada de oferta/demanda ni de precios de
    sustitutos (sólo baseline configurado en CFG). Por eso el engine NO fabrica
    un score numérico: declara honestamente "sin_datos_suficientes" en vez de
    inventar un número, y expone el baseline configurado únicamente como
    contexto informativo.
    """

    def process(
        self,
        snapshot_data: Dict[str, Any],
        supply_demand_cfg: Optional[Dict[str, Any]] = None,
        substitutes_cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        supply_demand_cfg = supply_demand_cfg or {}
        substitutes_cfg = substitutes_cfg or {}
        substitutes_list = substitutes_cfg.get("substitutes", [])

        if supply_demand_cfg:
            supply_label = supply_demand_cfg.get("supply_pressure_baseline", "desconocida")
            demand_label = supply_demand_cfg.get("demand_pressure_baseline", "desconocida")
            baseline_source = "baseline_configurado"
        else:
            fallback = (snapshot_data or {}).get("market_forces", {})
            supply_label = fallback.get("supply", "desconocida")
            demand_label = fallback.get("demand", "desconocida")
            baseline_source = "sin_configuracion"

        substitutes_label = ", ".join(s.get("substitute_id", "") for s in substitutes_list) if substitutes_list else "desconocido"

        return {
            "supply": supply_label,
            "demand": demand_label,
            "substitutes": substitutes_label,
            "supply_demand_pressure": {
                "status": "sin_datos_suficientes",
                "score": None,
                "baseline_source": baseline_source,
                "note": "No hay una fuente real de oferta/demanda observada; el baseline configurado es informativo, no se fabrica un score.",
            },
            "substitutes_pressure": {
                "status": "sin_datos_suficientes",
                "score": None,
                "items": substitutes_list,
                "note": "No hay observación real de precios de sustitutos; se listan las relaciones configuradas sin fabricar un score de impacto.",
            },
        }
