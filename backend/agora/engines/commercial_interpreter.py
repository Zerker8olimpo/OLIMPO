from typing import Any, Dict, Optional, Tuple

DEFAULT_SIGNAL = {"id": "informacion", "message": "No fue posible clasificar tu posición comercial con la configuración actual."}


class CommercialInterpreter:
    """
    Interpreta la posición comercial del usuario frente al mercado leyendo
    `rules.market_positions` (CFG_AGORA_COMMERCIAL_INTERPRETATION.json) en vez
    de una rama hardcodeada. Respeta CLAUDE.md sección 6.1: nunca certezas ni
    órdenes ("debes subir tu precio"), siempre señal prudente sobre un rango.
    """

    def process(self, observation: Dict[str, Any], margin: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        user_price = margin.get("user_price")
        market_price = observation.get("current_reference_price")

        if not market_price:
            pos_id = "mercado_sin_datos_suficientes"
            signal = {"id": "esperar", "message": "No hay datos de mercado suficientes para interpretar tu posición."}
        elif user_price:
            diff = (user_price - market_price) / market_price
            position, signal = self._match_position(diff, rules)
            pos_id = position.get("id", "posicion_no_clasificada") if position else "posicion_no_clasificada"
            signal = signal or DEFAULT_SIGNAL
        else:
            pos_id = "sin_precio_usuario"
            signal = {"id": "informacion", "message": "Observa la referencia de mercado para posicionar tu producto."}

        return {
            "market_position": pos_id,
            "margin_health": "margen_saludable" if margin.get("enabled") and market_price else "desconocida",
            "margin_risk": "bajo_si_costo_se_mantiene" if margin.get("enabled") and market_price else "desconocido",
            "suggested_signal": signal.get("id", "N/A"),
            "message": signal.get("message", "N/A")
        }

    def _match_position(self, diff: float, rules: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        positions = rules.get("market_positions", [])
        signals = rules.get("signals", {})

        for position in positions:
            diff_min = position.get("diff_min")
            diff_max = position.get("diff_max")
            if diff_min is not None and diff < diff_min:
                continue
            if diff_max is not None and diff >= diff_max:
                continue
            return position, signals.get(position.get("signal"))

        return None, None
