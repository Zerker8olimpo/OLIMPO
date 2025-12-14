"""
olimpo_ml_pipeline.py

OLIMPO ML Pipeline
- Orquesta CUÁNDO ejecutar OLIMPO ML Core
- Evita sobre-ejecución y sobresaltos
- Mantiene estado del aprendizaje

No decide CFG.
No aprende.
No analiza señales.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from typing import Dict, Any, Tuple

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
# OLIMPO ML Pipeline
# =========================

class OlimpoMLPipeline:
    """
    Orquestador temporal del ML.
    """

    def __init__(
        self,
        ml_core,
        cfg_dir: str,
        pipeline_state_file: str = "ML_PIPELINE_STATE.json",
        cfg_ml_file: str = "CFG_OLIMPO_ML.json",
    ):
        self.ml_core = ml_core
        self.cfg_dir = cfg_dir

        self.state_path = os.path.join(cfg_dir, pipeline_state_file)
        self.cfg_ml_path = os.path.join(cfg_dir, cfg_ml_file)

        # Estado del pipeline
        if not os.path.exists(self.state_path):
            save_json(self.state_path, {
                "last_run_time": None,
                "last_status": None,
                "run_count": 0
            })

        # Config ML (umbrales y políticas)
        self.cfg_ml = load_json(self.cfg_ml_path) if os.path.exists(self.cfg_ml_path) else {}

    # =========================
    # Ejecución principal
    # =========================

    def run(self, payload: Dict[str, Any], trigger: str = "auto") -> Dict[str, Any]:
        """
        Ejecuta OLIMPO ML Core si las condiciones lo permiten.

        trigger:
        - "manual": forzado
        - "auto": gobernado por reglas
        """

        state = load_json(self.state_path)
        now = datetime.utcnow()

        # -------------------------
        # 1) Decidir si ejecutar
        # -------------------------

        allow_run, reason = self._should_run(payload, state, trigger, now)

        if not allow_run:
            return {
                "pipeline_status": "skipped",
                "reason": reason,
                "timestamp": utc_now(),
            }

        # -------------------------
        # 2) Ejecutar ML Core
        # -------------------------

        ml_result = self.ml_core.ingest(payload)

        # -------------------------
        # 3) Actualizar estado
        # -------------------------

        state["last_run_time"] = utc_now()
        state["last_status"] = "executed"
        state["run_count"] = state.get("run_count", 0) + 1

        save_json(self.state_path, state)

        return {
            "pipeline_status": "executed",
            "reason": "conditions_met",
            "ml_result": ml_result,
            "timestamp": utc_now(),
        }

    # =========================
    # Lógica de decisión
    # =========================

    def _should_run(
        self,
        payload: Dict[str, Any],
        state: Dict[str, Any],
        trigger: str,
        now: datetime,
    ) -> Tuple[bool, str]:

        # Forzado manual
        if trigger == "manual":
            return True, "manual_trigger"

        # Cargar configuración ML
        cooldown_hours = int(self.cfg_ml.get("cooldown_hours", 24))
        max_idle_hours = int(self.cfg_ml.get("max_idle_hours", 72))
        error_threshold = float(self.cfg_ml.get("dt_error_threshold", 0.25))

        # Cooldown
        last_run = state.get("last_run_time")
        if last_run:
            try:
                last_run_dt = datetime.fromisoformat(last_run)
                if now - last_run_dt < timedelta(hours=cooldown_hours):
                    return False, "cooldown_active"
            except Exception:
                pass  # si hay error de parseo, seguimos de forma conservadora

        # Shock activo
        shock_flag = payload.get("analysis_results", {}).get("shock", {}).get("shock_flag", 0)
        if shock_flag:
            return True, "shock_active"

        # Error del Digital Twin
        dt_error = payload.get("helios_results", {}).get("dt", {}).get("error", {})
        mape = float(dt_error.get("mape", 0.0)) if dt_error else 0.0
        if mape >= error_threshold:
            return True, "dt_error_high"

        # Tiempo máximo sin ML
        if last_run:
            try:
                if now - last_run_dt >= timedelta(hours=max_idle_hours):
                    return True, "max_idle_exceeded"
            except Exception:
                pass

        return False, "conditions_not_met"
