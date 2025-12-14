"""
ml_dispatcher.py

MLDispatcher es un adaptador de comunicación entre OSEngine_CORE y OLIMPO ML Core.

Responsabilidades:
- Validar estructura mínima del payload
- Sellar metadata de despacho
- Enviar el payload completo a OLIMPO ML Core

NO:
- Analiza datos
- Extrae features
- Decide ajustes
- Modifica CFG
- Aprende

Este módulo es deliberadamente simple.
"""

from datetime import datetime
from typing import Dict, Any, List
import logging


class MLDispatcher:
    def __init__(self, ml_core):
        """
        ml_core: instancia de OLIMPO ML Core
        """
        self.ml_core = ml_core
        self.logger = logging.getLogger("MLDispatcher")

    def dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Despacha un payload completo desde OSEngine_CORE hacia OLIMPO ML Core.

        Payload esperado:
        {
            "context": {...},
            "analysis_results": {...},
            "helios_results": {...},
            "proposals": [...],
            "timestamp": "ISO-8601"
        }
        """

        # ===============================
        # 1. Validación estructural mínima
        # ===============================

        required_keys: List[str] = [
            "context",
            "analysis_results",
            "helios_results",
            "proposals",
            "timestamp",
        ]

        for key in required_keys:
            if key not in payload:
                self.logger.warning(f"Payload inválido: falta la clave '{key}'")
                return {
                    "status": "invalid_payload",
                    "missing_key": key,
                    "timestamp": self._now(),
                }

        if not isinstance(payload["analysis_results"], dict):
            self.logger.warning("analysis_results debe ser dict")
            return {
                "status": "invalid_payload",
                "reason": "analysis_results_not_dict",
                "timestamp": self._now(),
            }

        if not isinstance(payload["helios_results"], dict):
            self.logger.warning("helios_results debe ser dict")
            return {
                "status": "invalid_payload",
                "reason": "helios_results_not_dict",
                "timestamp": self._now(),
            }

        if not isinstance(payload["proposals"], list):
            self.logger.warning("proposals debe ser una lista")
            return {
                "status": "invalid_payload",
                "reason": "proposals_not_list",
                "timestamp": self._now(),
            }

        # ===============================
        # 2. Sellado de metadata
        # ===============================

        payload["dispatcher_metadata"] = {
            "dispatcher": "MLDispatcher",
            "dispatch_time": self._now(),
            "version": "1.0",
        }

        # ===============================
        # 3. Despacho a OLIMPO ML Core
        # ===============================

        try:
            self.ml_core.ingest(payload)
        except Exception as e:
            self.logger.exception("Error al despachar payload a OLIMPO ML Core")
            return {
                "status": "dispatch_error",
                "error": str(e),
                "timestamp": self._now(),
            }

        # ===============================
        # 4. Acknowledgement
        # ===============================

        return {
            "status": "dispatched",
            "proposal_count": len(payload["proposals"]),
            "timestamp": payload["timestamp"],
        }

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()
