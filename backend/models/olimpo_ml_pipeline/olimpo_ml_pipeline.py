"""
OLIMPO ML Pipeline (refactorizado)

Responsabilidades:
- Ejecutar HELIOS Digital Twin por consulta de usuario (TIEMPO REAL)
- Orquestar ciclo de ML gobernado (NO crítico)
- Construir contrato estándar de salida (Fase A)

NO:
- No decide CFG directamente
- No calcula modelos
- No analiza señales internas
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple

# Motores
from digital_twin.helios_engine import HeliosEngine
from models.olimpo_ml_core.olimpo_ml_core import OlimpoMLCore


# =========================
# Utilidades
# =========================

def utc_now() -> str:
    return datetime.utcnow().isoformat()


def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# Pipeline principal
# =========================

class OlimpoMLPipeline:
    """
    Pipeline operativo de OLIMPO.
    """

    def __init__(
        self,
        cfg_dir: str,
        enable_logs: bool = False,
        pipeline_state_file: str = "ML_PIPELINE_STATE.json",
    ):
        self.cfg_dir = cfg_dir

        # Estado
        self.state_path = os.path.join(cfg_dir, pipeline_state_file)
        if not os.path.exists(self.state_path):
            save_json(self.state_path, {
                "last_ml_run": None,
                "ml_run_count": 0
            })

        # Motores
        self.helios = HeliosEngine(enable_logs=enable_logs)
        self.ml_core = OlimpoMLCore(cfg_dir=cfg_dir)

    # =====================================================
    # MODO 1 — CONSULTA USUARIO (CRÍTICO / TIEMPO REAL)
    # =====================================================

    def run_user_query(
        self,
        epsilon_input: Dict[str, Any],
        sigma_input: Dict[str, Any],
        poseidon_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ejecuta HELIOS Digital Twin SIEMPRE.
        Retorna contrato estándar Fase A.
        """

        helios_raw = self.helios.run_digital_twin(
            epsilon_input=epsilon_input,
            sigma_input=sigma_input,
            poseidon_input=poseidon_input,
            write_output=False
        )

        return self._build_contract_from_helios(
            helios_raw=helios_raw,
            epsilon_input=epsilon_input,
            sigma_input=sigma_input,
            poseidon_input=poseidon_input,
        )

    # =====================================================
    # MODO 2 — CICLO ML GOBERNADO (NO CRÍTICO)
    # =====================================================

    def run_ml_cycle(
        self,
        payload: Dict[str, Any],
        trigger: str = "auto"
    ) -> Dict[str, Any]:
        """
        Ejecuta OLIMPO ML Core bajo reglas gobernadas.
        """

        state = load_json(self.state_path)

        ml_result = self.ml_core.ingest(payload)

        state["last_ml_run"] = utc_now()
        state["ml_run_count"] = state.get("ml_run_count", 0) + 1
        save_json(self.state_path, state)

        return {
            "status": "ml_cycle_executed",
            "timestamp": utc_now(),
            "result": ml_result
        }

    # =====================================================
    # CONSTRUCCIÓN CONTRATO FASE A
    # =====================================================

    def _build_contract_from_helios(
        self,
        helios_raw: Dict[str, Any],
        epsilon_input: Dict[str, Any],
        sigma_input: Dict[str, Any],
        poseidon_input: Dict[str, Any],
    ) -> Dict[str, Any]:

        epsilon = helios_raw.get("HELIOS_DIGITALTWIN", {}).get("epsilon", {}).get("productos", [{}])[0]
        sigma = helios_raw.get("HELIOS_DIGITALTWIN", {}).get("sigma", {}).get("productos", [{}])[0]
        poseidon = helios_raw.get("HELIOS_DIGITALTWIN", {}).get("poseidon", {}).get("productos", [{}])[0]

        return {
            "meta": {
                "engine": "OLIMPO",
                "timestamp": utc_now(),
                "version": "1.0",
            },
            "input_summary": {
                "product_id": epsilon_input.get("product_id"),
                "market_id": epsilon_input.get("market_id"),
                "horizonte_meses": epsilon_input.get("horizonte_meses"),
            },
            "signals": {
                "phi_series": epsilon.get("phi_series"),
                "g_series": epsilon.get("g_series"),
                "psi": sigma.get("psi"),
            },
            "metrics": {
                "forecast_base": epsilon.get("forecast_base"),
                "forecast_dt": epsilon.get("forecast_dt"),
                "demanda_dt": sigma.get("demanda_dt"),
            },
            "decision_support": {
                "compra_sugerida": epsilon.get("compra_sugerida"),
                "eoq_dt": sigma.get("eoq_dt"),
                "rop_dt": sigma.get("rop_dt"),
            },
            "risk": {
                "nivel": poseidon.get("risk_level", "UNKNOWN"),
            },
            "charts": [
                {
                    "id": "forecast_dt",
                    "type": "line",
                    "data": epsilon.get("forecast_dt"),
                }
            ],
            "warnings": []
        }
