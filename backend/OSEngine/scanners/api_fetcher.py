import asyncio
from datetime import datetime
from typing import Dict, Any, List

from backend.core.economic_indicators_client import EconomicIndicatorsClient

DEFAULT_INDICATOR_CODES = ["dolar", "ipc", "uf"]


class APIFetcher:
    """
    APIFetcher
    ----------
    Scanner de APIs externas.
    Captura datos crudos y declara calidad de la observación.
    """

    def __init__(self, client: EconomicIndicatorsClient = None):
        self.client = client or EconomicIndicatorsClient()

    def fetch(self) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat()

        data: Dict[str, Any] = {}
        errors: List[str] = []
        missing_fields: List[str] = []

        try:
            indicators = asyncio.run(self.client.get_indicators(DEFAULT_INDICATOR_CODES))
            for codigo, result in indicators.items():
                if result.get("status") == "ok":
                    data[codigo] = {
                        "valor": result.get("valor"),
                        "fecha": result.get("fecha"),
                        "variacion_6m": result.get("variacion_6m"),
                    }
                else:
                    missing_fields.append(codigo)
                    if result.get("error"):
                        errors.append(f"{codigo}: {result['error']}")
        except Exception as e:
            errors.append(str(e))

        # --------------------------------------------------
        # Evaluación de calidad
        # --------------------------------------------------
        if not data:
            status = "failed"
            confidence = 0.0
        elif missing_fields:
            status = "partial"
            confidence = 0.4
        else:
            status = "ok"
            confidence = 0.9

        return {
            "source": "api",
            "timestamp": timestamp,
            "data": data,
            "quality": {
                "status": status,
                "confidence": confidence,
                "missing_fields": missing_fields,
                "errors": errors
            }
        }
