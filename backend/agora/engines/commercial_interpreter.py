from typing import Dict, Any

class CommercialInterpreter:
    def process(self, observation: Dict[str, Any], margin: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        # Lógica simplificada de interpretación
        user_price = margin.get("user_price")
        market_price = observation["current_reference_price"]
        
        if user_price:
            diff = (user_price - market_price) / market_price
            # Buscar en rules.market_positions
            # Por ahora hardcoded para el ejemplo
            if -0.10 < diff < -0.02:
                pos_id = "precio_usuario_levemente_bajo_mercado"
                signal = rules.get("signals", {}).get("caution", {})
            else:
                pos_id = "precio_fuera_de_rango_ejemplo"
                signal = {"id": "revisar", "message": "Tu precio requiere revisión frente al mercado."}
        else:
            pos_id = "sin_precio_usuario"
            signal = {"id": "informacion", "message": "Observa la referencia de mercado para posicionar tu producto."}

        return {
            "market_position": pos_id,
            "margin_health": "margen_saludable" if margin.get("enabled") else "desconocida",
            "margin_risk": "bajo_si_costo_se_mantiene" if margin.get("enabled") else "desconocido",
            "suggested_signal": signal.get("id", "N/A"),
            "message": signal.get("message", "N/A")
        }
