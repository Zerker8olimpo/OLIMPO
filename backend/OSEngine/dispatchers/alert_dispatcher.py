from datetime import datetime
from typing import Dict, Any


class AlertDispatcher:
    """
    AlertDispatcher
    ----------------
    Traduce el estado del sistema en alertas operativas.
    No ejecuta decisiones ni modifica el sistema.
    """

    def dispatch(
        self,
        system_state: Dict[str, Any],
        cfg: Dict[str, Any]
    ) -> Dict[str, Any]:

        timestamp = datetime.utcnow().isoformat()
        context = system_state.get("context", {})

        psi = system_state.get("psi", {})
        shock = system_state.get("shock", {})

        psi_value = psi.get("effective", 0.0)
        psi_confidence = psi.get("confidence", 0.0)
        shock_flag = shock.get("shock_flag", 0)

        alert_triggered = False
        alert_level = "none"
        message = ""

        # --------------------------------------------------
        # Evaluación simple por niveles
        # --------------------------------------------------
        levels = cfg["levels"]

        if psi_value >= levels["critical"] and psi_confidence >= cfg["confidence_min"]:
            alert_triggered = True
            alert_level = "critical"
            message = "Impacto crítico detectado. Revisión inmediata recomendada."

        elif psi_value >= levels["warning"] and psi_confidence >= cfg["confidence_min"]:
            alert_triggered = True
            alert_level = "warning"
            message = "Impacto elevado detectado. Se recomienda monitoreo."

        elif shock_flag and cfg["notify_on_shock"]:
            alert_triggered = True
            alert_level = "info"
            message = "Shock detectado. Contexto bajo observación."

        return {
            "alert_triggered": alert_triggered,
            "alert_level": alert_level,
            "message": message,
            "confidence": round(psi_confidence, 3),
            "timestamp": timestamp,
            "context": context
        }
