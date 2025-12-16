from datetime import datetime
from typing import Dict, Any, List


class DTDispatcher:
    """
    DTDispatcher
    ------------
    Envía el estado del sistema al Digital Twin (HELIOS).
    No ejecuta simulaciones ni interpreta resultados.
    """

    def dispatch(
        self,
        system_state: Dict[str, Any],
        cfg: Dict[str, Any]
    ) -> Dict[str, Any]:

        timestamp = datetime.utcnow().isoformat()
        errors: List[str] = []

        context = system_state.get("context", {})

        # --------------------------------------------------
        # Validación mínima del estado
        # --------------------------------------------------
        required_blocks = cfg.get("required_blocks", [])

        for block in required_blocks:
            if block not in system_state:
                errors.append(f"Missing block: {block}")

        # --------------------------------------------------
        # Preparación de snapshot para Digital Twin
        # --------------------------------------------------
        dispatched = False
        status = "failed"

        if not errors:
            try:
                payload = {
                    "timestamp": timestamp,
                    "state": system_state
                }

                # --------------------------------------------------
                # Aquí se conectará HELIOS en el futuro
                # (API, cola, archivo, etc.)
                # --------------------------------------------------
                # Example:
                # helios_client.send(payload)

                dispatched = True
                status = "ok"

            except Exception as e:
                errors.append(str(e))

        return {
            "dispatched": dispatched,
            "target": "digital_twin",
            "status": status,
            "errors": errors,
            "timestamp": timestamp,
            "context": context
        }
