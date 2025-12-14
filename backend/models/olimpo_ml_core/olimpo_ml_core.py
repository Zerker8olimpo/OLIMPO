"""
olimpo_ml_core.py

OLIMPO ML Core (gobernado)
- Recibe payload desde MLDispatcher: context + analysis_results + helios_results + proposals + timestamp
- Valida propuestas con parameter_path_map.json (lista blanca)
- Decide: apply / defer / reject
- Aplica cambios SOLO como patches (CFG_PATCHES.json), sin romper estructura de CFG base
- Registra historial de decisiones (ML_HISTORY.json) y respeta cooldown
- Genera recomendaciones de indicadores (explicables) por producto/mercado

Nota importante:
- Este módulo NO ejecuta scanners ni OSEngine.
- OSEngine genera el payload y las propuestas; ML Core gobierna y aprende.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional


# =========================
# Utilidades base
# =========================

def utc_now() -> str:
    return datetime.utcnow().isoformat()

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_nested(cfg: Dict[str, Any], path: str) -> Any:
    cur = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def set_nested(cfg: Dict[str, Any], path: str, value: Any) -> bool:
    keys = path.split(".")
    cur = cfg
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            return False
        cur = cur[k]
    last = keys[-1]
    if last not in cur:
        return False
    cur[last] = value
    return True


# =========================
# Decisiones
# =========================

class Decision:
    APPLY = "apply"
    DEFER = "defer"
    REJECT = "reject"


# =========================
# OLIMPO ML Core
# =========================

class OlimpoMLCore:
    """
    OLIMPO ML Core (robusto y gobernado)

    API principal:
    - ingest(payload) -> resultado del ciclo ML

    Payload esperado (desde OSEngine_CORE vía MLDispatcher):
    {
      "context": {...},
      "analysis_results": {...},
      "helios_results": {...},
      "proposals": [...],  # CFGProposal[]
      "timestamp": "ISO-8601"
    }
    """

    def __init__(
        self,
        cfg_dir: str,
        parameter_map_file: str = "parameter_path_map.json",
        patches_file: str = "CFG_PATCHES.json",
        history_file: str = "ML_HISTORY.json",
        cfg_limits_file: str = "CFG_LIMITES_SUP_INF.json",
        cfg_ml_file: str = "CFG_OLIMPO_ML.json",
    ):
        self.cfg_dir = cfg_dir

        self.parameter_map_path = os.path.join(cfg_dir, parameter_map_file)
        self.patches_path = os.path.join(cfg_dir, patches_file)
        self.history_path = os.path.join(cfg_dir, history_file)

        self.cfg_limits_path = os.path.join(cfg_dir, cfg_limits_file)
        self.cfg_ml_path = os.path.join(cfg_dir, cfg_ml_file)

        # Carga lista blanca (obligatoria)
        if not os.path.exists(self.parameter_map_path):
            raise FileNotFoundError(f"parameter_path_map.json no existe en: {self.parameter_map_path}")
        self.parameter_map = load_json(self.parameter_map_path)

        # Archivos auxiliares
        if not os.path.exists(self.history_path):
            save_json(self.history_path, {"events": [], "usage": {"products": {}, "markets": {}, "modules": {}}})

        if not os.path.exists(self.patches_path):
            save_json(self.patches_path, {"version": "1.0", "patches": []})

        # Cargas opcionales (si existen)
        self.cfg_limits = load_json(self.cfg_limits_path) if os.path.exists(self.cfg_limits_path) else {}
        self.cfg_ml = load_json(self.cfg_ml_path) if os.path.exists(self.cfg_ml_path) else {}

    # -----------------------------
    # Entrada (desde MLDispatcher)
    # -----------------------------
    def ingest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Punto de entrada único. MLDispatcher llama a este método.
        """
        self._validate_payload_minimal(payload)

        context = payload.get("context", {}) or {}
        analysis_results = payload.get("analysis_results", {}) or {}
        helios_results = payload.get("helios_results", {}) or {}
        proposals = payload.get("proposals", []) or []

        # Derivar condiciones activas (conservador)
        active_conditions = self._derive_active_conditions(analysis_results)

        # Ejecutar ciclo gobernado
        result = self._run_governed_cycle(
            context=context,
            analysis_results=analysis_results,
            helios_results=helios_results,
            proposals=proposals,
            active_conditions=active_conditions,
        )

        return result

    # -----------------------------
    # Ciclo ML gobernado
    # -----------------------------
    def _run_governed_cycle(
        self,
        context: Dict[str, Any],
        analysis_results: Dict[str, Any],
        helios_results: Dict[str, Any],
        proposals: List[Dict[str, Any]],
        active_conditions: List[str],
    ) -> Dict[str, Any]:

        decisions: List[Dict[str, Any]] = []
        applied: List[Dict[str, Any]] = []
        deferred: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for prop in proposals:
            decision, reason = self._evaluate_proposal(prop, active_conditions)
            pid = prop.get("metadata", {}).get("proposal_id", "UNKNOWN")

            decisions.append({"proposal_id": pid, "decision": decision, "reason": reason})

            if decision == Decision.APPLY:
                ok, apply_reason, change = self._apply_proposal_as_patch(prop)
                if ok:
                    applied.append(change)
                else:
                    rejected.append({"proposal_id": pid, "reason": f"failed_apply:{apply_reason}"})
            elif decision == Decision.DEFER:
                deferred.append({"proposal_id": pid, "reason": reason})
            else:
                rejected.append({"proposal_id": pid, "reason": reason})

        # Registrar historial (un solo evento por ciclo)
        self._log_event(
            context=context,
            analysis_results=analysis_results,
            helios_results=helios_results,
            proposals=proposals,
            decisions=decisions,
            applied=applied
        )

        # Aprendizaje ligero (por ahora: contadores de uso + soporte a cooldown)
        self._learn_usage(context, analysis_results)

        # Recomendador de indicadores/módulos
        recommendations = self._recommend_indicators(context, analysis_results, helios_results)

        return {
            "timestamp": utc_now(),
            "context": context,
            "summary": {
                "proposals_received": len(proposals),
                "applied": len(applied),
                "deferred": len(deferred),
                "rejected": len(rejected),
            },
            "decisions": decisions,
            "applied_changes": applied,
            "recommendations": recommendations,
        }

    # -----------------------------
    # Validación del payload
    # -----------------------------
    def _validate_payload_minimal(self, payload: Dict[str, Any]) -> None:
        required = ["context", "analysis_results", "helios_results", "proposals", "timestamp"]
        for k in required:
            if k not in payload:
                raise ValueError(f"Payload inválido: falta '{k}'")
        if not isinstance(payload["analysis_results"], dict):
            raise ValueError("Payload inválido: analysis_results debe ser dict")
        if not isinstance(payload["helios_results"], dict):
            raise ValueError("Payload inválido: helios_results debe ser dict")
        if not isinstance(payload["proposals"], list):
            raise ValueError("Payload inválido: proposals debe ser list")

    def _derive_active_conditions(self, analysis_results: Dict[str, Any]) -> List[str]:
        conditions: List[str] = []
        shock_flag = analysis_results.get("shock", {}).get("shock_flag", 0)
        if shock_flag:
            conditions.append("active_shock")
        return conditions

    # -----------------------------
    # Evaluación / gobernanza
    # -----------------------------
    def _evaluate_proposal(self, proposal: Dict[str, Any], active_conditions: List[str]) -> Tuple[str, str]:
        target = proposal.get("target", {})
        cfg_file = target.get("cfg_file")
        path = target.get("parameter_path")
        ptype = proposal.get("proposal", {}).get("type")

        if not cfg_file or not path:
            return Decision.REJECT, "missing_target_fields"

        allowed_cfg = self.parameter_map.get("cfg_files", {}).get(cfg_file)
        if not allowed_cfg:
            return Decision.REJECT, f"cfg_file_not_allowed:{cfg_file}"

        allowed_param = allowed_cfg.get(path)
        if not allowed_param:
            return Decision.REJECT, f"parameter_path_not_allowed:{path}"

        forbidden = set(allowed_param.get("forbidden_conditions", [])) | set(proposal.get("validation", {}).get("forbidden_conditions", []))
        if any(cond in forbidden for cond in active_conditions):
            return Decision.DEFER, "forbidden_condition_active"

        # Confianza mínima (fallback conservador)
        min_conf = float(proposal.get("validation", {}).get("min_confidence_required", 0.70))
        conf = float(proposal.get("confidence", {}).get("proposal_confidence", 0.0))
        if conf < min_conf:
            return Decision.DEFER, "low_confidence"

        # Cooldown
        cooldown_days = int(allowed_param.get("cooldown_days", 14))
        if self._is_in_cooldown(cfg_file, path, cooldown_days):
            return Decision.DEFER, "cooldown_active"

        # Tipo permitido
        allowed_adjust = allowed_param.get("adjustment", "delta")
        if allowed_adjust == "freeze" and ptype != "freeze":
            return Decision.REJECT, "adjustment_type_mismatch"
        if allowed_adjust in ("delta", "range") and ptype not in ("delta", "range", "freeze"):
            return Decision.REJECT, "proposal_type_invalid"

        return Decision.APPLY, "ok"

    def _is_in_cooldown(self, cfg_file: str, path: str, cooldown_days: int) -> bool:
        hist = load_json(self.history_path)
        events = hist.get("events", [])
        if not events:
            return False

        cutoff = datetime.utcnow() - timedelta(days=cooldown_days)
        for ev in reversed(events):
            ts = ev.get("timestamp")
            applied = ev.get("applied", [])
            if not applied:
                continue
            for a in applied:
                if a.get("cfg_file") == cfg_file and a.get("parameter_path") == path:
                    try:
                        t = datetime.fromisoformat(ts)
                        if t > cutoff:
                            return True
                        return False
                    except Exception:
                        # conservador: si no podemos parsear, consideramos cooldown activo
                        return True
        return False

    # -----------------------------
    # Aplicación (patch recomendado)
    # -----------------------------
    def _apply_proposal_as_patch(self, proposal: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Aplica SOLO como patch (no reescribe el CFG base).
        Retorna (ok, reason, change_record)
        """
        target = proposal["target"]
        cfg_file = target["cfg_file"]
        path = target["parameter_path"]

        cfg_path = os.path.join(self.cfg_dir, cfg_file)
        if not os.path.exists(cfg_path):
            return False, "cfg_file_missing_on_disk", {}

        cfg_base = load_json(cfg_path)
        current_val = get_nested(cfg_base, path)
        if current_val is None:
            return False, "parameter_path_missing_in_cfg", {}

        allowed_param = self.parameter_map["cfg_files"][cfg_file][path]
        ptype = proposal.get("proposal", {}).get("type", "delta")

        # Calcular new_val
        if ptype == "freeze":
            new_val = current_val
        elif ptype == "delta":
            delta = float(proposal["proposal"].get("delta", 0.0))
            max_delta = float(allowed_param.get("max_delta", abs(delta)))
            if abs(delta) > max_delta:
                delta = max_delta if delta > 0 else -max_delta
            new_val = current_val + delta
        elif ptype == "range":
            suggested = proposal["proposal"].get("suggested_value")
            if suggested is None:
                return False, "range_without_suggested_value", {}
            new_val = suggested
        else:
            return False, "unknown_proposal_type", {}

        # Hard limits
        min_v = float(allowed_param.get("min", new_val))
        max_v = float(allowed_param.get("max", new_val))
        if new_val < min_v:
            new_val = min_v
        if new_val > max_v:
            new_val = max_v

        # Type enforcement
        expected_type = allowed_param.get("type", "float")
        if expected_type == "int":
            new_val = int(round(float(new_val)))
        elif expected_type == "bool":
            new_val = bool(new_val)
        else:
            new_val = float(new_val)

        # Guardar patch
        patches = load_json(self.patches_path)
        change = {
            "timestamp": utc_now(),
            "cfg_file": cfg_file,
            "parameter_path": path,
            "previous_value": current_val,
            "new_value": new_val,
            "proposal_id": proposal.get("metadata", {}).get("proposal_id"),
            "source_module": proposal.get("metadata", {}).get("source_module"),
        }
        patches["patches"].append(change)
        save_json(self.patches_path, patches)

        return True, "ok", change

    # -----------------------------
    # Construir CFG efectivo (base + patches)
    # -----------------------------
    def get_effective_cfg(self, cfg_file: str) -> Dict[str, Any]:
        """
        Devuelve una vista del CFG efectivo aplicando patches válidos sobre el CFG base.
        (No escribe nada; útil para HELIOS si decides leer 'cfg efectivo' en runtime)
        """
        cfg_path = os.path.join(self.cfg_dir, cfg_file)
        cfg_base = load_json(cfg_path)

        patches = load_json(self.patches_path).get("patches", [])
        for p in patches:
            if p.get("cfg_file") != cfg_file:
                continue
            path = p.get("parameter_path")
            new_val = p.get("new_value")
            # Solo aplica si la ruta existe (protección)
            if get_nested(cfg_base, path) is not None:
                set_nested(cfg_base, path, new_val)

        return cfg_base

    # -----------------------------
    # Historial y aprendizaje
    # -----------------------------
    def _log_event(
        self,
        context: Dict[str, Any],
        analysis_results: Dict[str, Any],
        helios_results: Dict[str, Any],
        proposals: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        applied: List[Dict[str, Any]],
    ) -> None:
        hist = load_json(self.history_path)

        event = {
            "timestamp": utc_now(),
            "context": context,
            "signals": {
                "psi": analysis_results.get("psi", {}),
                "phi": analysis_results.get("phi", {}),
                "volatility": analysis_results.get("volatility", {}),
                "shock": analysis_results.get("shock", {}),
                "trend": analysis_results.get("trend", {}),
            },
            "dt_error": helios_results.get("dt", {}).get("error", {}),
            "proposal_count": len(proposals),
            "decisions": decisions,
            "applied": applied,
        }

        hist["events"].append(event)
        save_json(self.history_path, hist)

    def _learn_usage(self, context: Dict[str, Any], analysis_results: Dict[str, Any]) -> None:
        """
        Aprendizaje inicial y seguro: solo persistimos patrones de uso (mercado/producto/módulos).
        No toca CFG.
        """
        hist = load_json(self.history_path)
        usage = hist.get("usage", {"products": {}, "markets": {}, "modules": {}})

        product_id = context.get("product_id")
        market_id = context.get("market_id")

        if product_id:
            usage["products"][product_id] = usage["products"].get(product_id, 0) + 1
        if market_id:
            usage["markets"][market_id] = usage["markets"].get(market_id, 0) + 1

        # inferencia simple de módulos usados según señales presentes
        modules = []
        if analysis_results.get("shock"):
            modules.append("ShockDetector")
        if analysis_results.get("volatility"):
            modules.append("VolatilityEstimator")
        if analysis_results.get("trend"):
            modules.append("TrendAnalyzer")
        if analysis_results.get("phi"):
            modules.append("SensitivityPhi")
        if analysis_results.get("psi"):
            modules.append("ImpactPsi")

        for m in modules:
            usage["modules"][m] = usage["modules"].get(m, 0) + 1

        hist["usage"] = usage
        save_json(self.history_path, hist)

    # -----------------------------
    # Recomendador (explicable)
    # -----------------------------
    def _recommend_indicators(
        self,
        context: Dict[str, Any],
        analysis_results: Dict[str, Any],
        helios_results: Dict[str, Any]
    ) -> Dict[str, Any]:

        psi = float(analysis_results.get("psi", {}).get("effective", 0.0))
        psi_conf = float(analysis_results.get("psi", {}).get("confidence", 0.0))
        phi = float(analysis_results.get("phi", {}).get("value", 0.0))
        phi_conf = float(analysis_results.get("phi", {}).get("confidence", 0.0))
        vol = float(analysis_results.get("volatility", {}).get("sigma", {}).get("total", 0.0))
        trend_dir = analysis_results.get("trend", {}).get("direction", "flat")

        dt_err = helios_results.get("dt", {}).get("error", {}) or {}
        mape = float(dt_err.get("mape", 0.0)) if dt_err else 0.0
        bias = float(dt_err.get("bias", 0.0)) if dt_err else 0.0

        indicators: List[str] = []
        modules: List[str] = []
        notes: List[str] = []

        # Producto/mercado en contexto
        if context.get("product_id"):
            notes.append(f"Contexto producto: {context['product_id']}")
        if context.get("market_id"):
            notes.append(f"Contexto mercado: {context['market_id']}")

        # Reglas explicables
        if psi_conf >= 0.6 and psi >= 0.7:
            indicators += ["ψ (impacto)", "shock_intensity", "volatilidad total", "lead time esperado", "safety stock dinámico", "OTIF/Fill Rate"]
            modules += ["OSEngine: ImpactPsi", "OSEngine: ShockDetector", "OSEngine: VolatilityEstimator", "HELIOS Digital Twin"]
            notes.append("Alta exposición: priorizar control de riesgo, buffers y continuidad operacional.")

        if phi_conf >= 0.6 and phi >= 0.6:
            indicators += ["φ (sensibilidad mercado-demanda)", "correlación señales externas vs demanda", "elasticidad", "IPC/FX/commodities relevantes"]
            modules += ["OSEngine: SensitivityPhi", "HELIOS Mercados", "HELIOS COMEX"]
            notes.append("Alta sensibilidad: el entorno explica la demanda; conviene mirar macro/COMEX.")

        if vol >= 1.0:
            indicators += ["EWMA σ", "volatilidad combinada", "breakpoints/fases", "CV demanda"]
            modules += ["OSEngine: VolatilityEstimator", "OSEngine: TrendAnalyzer"]
            notes.append("Volatilidad elevada: reducir sobre-reacción; usar ventanas consistentes y límites.")

        if mape >= 0.2 or abs(bias) >= 0.1:
            indicators += ["MAPE", "Bias", "Tracking Signal", "error rolling (4-12)", "Backtesting por SKU/mercado"]
            modules += ["HELIOS Digital Twin", "OLIMPO ML Core (calibración CFG)"]
            notes.append("Error del twin elevado: calibrar parámetros tunables y revisar supuestos estructurales.")

        if trend_dir in ("up", "down"):
            indicators += ["pendiente rolling", "confianza tendencia", "estabilidad (CV)", "rupturas (breakpoints)"]
            modules += ["OSEngine: TrendAnalyzer"]
            notes.append("Tendencia detectada: ajustar política de ventanas y vigilar quiebres de tendencia.")

        # Deduplicación
        indicators = list(dict.fromkeys(indicators))
        modules = list(dict.fromkeys(modules))

        return {
            "indicators": indicators,
            "suggested_modules": modules,
            "notes": notes
        }
