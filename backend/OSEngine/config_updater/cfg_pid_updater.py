from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


class PIDUpdater:
    """
    PIDUpdater (propuestas, no cambios)
    ----------------------------------
    Genera CFGProposal para parámetros PID (Kp, Ki, Kd).
    NO escribe CFG. NO aplica cambios. Solo propone deltas/rangos/freezes.
    """

    def propose(
        self,
        analysis_results: Dict[str, Any],
        cfg_limits: Dict[str, Any],
        cfg_olimpo_ml: Optional[Dict[str, Any]] = None,
        scope: str = "global",
        entity_id: str = "ALL",
    ) -> List[Dict[str, Any]]:

        # Señales mínimas recomendadas
        psi = analysis_results.get("psi", {}).get("effective", 0.0)
        psi_conf = analysis_results.get("psi", {}).get("confidence", 0.0)

        shock_flag = analysis_results.get("shock", {}).get("shock_flag", 0)
        trend_conf = analysis_results.get("trend", {}).get("confidence", 0.0)
        vol = analysis_results.get("volatility", {}).get("sigma", {}).get("total", 0.0)

        # Guardrails (si falta algo, se usa fallback conservador)
        max_delta = float(cfg_limits.get("pid", {}).get("max_delta", 0.05))
        cooldown = cfg_limits.get("pid", {}).get("cooldown_period", "14d")

        kp_min = float(cfg_limits.get("pid", {}).get("kp_min", 0.0))
        kp_max = float(cfg_limits.get("pid", {}).get("kp_max", 10.0))
        ki_min = float(cfg_limits.get("pid", {}).get("ki_min", 0.0))
        ki_max = float(cfg_limits.get("pid", {}).get("ki_max", 10.0))
        kd_min = float(cfg_limits.get("pid", {}).get("kd_min", 0.0))
        kd_max = float(cfg_limits.get("pid", {}).get("kd_max", 10.0))

        min_conf_apply = float(cfg_limits.get("pid", {}).get("min_confidence_required", 0.70))

        proposals: List[Dict[str, Any]] = []

        # Regla 1: si hay shock activo, proponer FREEZE (evita sobre-reacción)
        if shock_flag:
            proposals.append(self._proposal_freeze(
                cfg_file="CFG_OLIMPO_ML.json",
                parameter_path="pid.freeze",
                reason="active_shock",
                signals={"psi": psi, "psi_conf": psi_conf, "trend_conf": trend_conf, "vol": vol},
                cooldown=cooldown,
                scope=scope,
                entity_id=entity_id
            ))
            return proposals

        # Regla 2: solo proponer ajustes si hay señal suficientemente confiable
        if psi_conf < min_conf_apply or trend_conf < 0.5:
            return proposals

        # Heurística conservadora:
        # - Si volatilidad alta sostenida, bajar agresividad proporcional (↓Kp, ↑Kd levemente)
        # - Si psi alto con tendencia estable, subir Ki levemente para corregir sesgo persistente
        # Nota: aquí NO “decidimos”, solo proponemos.
        if vol > float(cfg_limits.get("pid", {}).get("volatility_high", 1.0)):
            dk = -_clamp(0.5 * max_delta, 0.0, max_delta)  # bajar Kp
            proposals.append(self._proposal_delta(
                cfg_file="CFG_OLIMPO_ML.json",
                parameter_path="pid.kp",
                delta=dk,
                hard_limits={"min": kp_min, "max": kp_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.9, psi_conf),
                pattern="high_volatility_reduce_gain",
                signals={"psi": psi, "psi_conf": psi_conf, "trend_conf": trend_conf, "vol": vol},
                scope=scope,
                entity_id=entity_id
            ))

            dd = _clamp(0.25 * max_delta, 0.0, max_delta)  # subir Kd un poco
            proposals.append(self._proposal_delta(
                cfg_file="CFG_OLIMPO_ML.json",
                parameter_path="pid.kd",
                delta=dd,
                hard_limits={"min": kd_min, "max": kd_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.85, psi_conf),
                pattern="high_volatility_damping",
                signals={"psi": psi, "psi_conf": psi_conf, "trend_conf": trend_conf, "vol": vol},
                scope=scope,
                entity_id=entity_id
            ))

        if psi > float(cfg_limits.get("pid", {}).get("psi_high", 0.7)) and trend_conf >= 0.65:
            di = _clamp(0.25 * max_delta, 0.0, max_delta)
            proposals.append(self._proposal_delta(
                cfg_file="CFG_OLIMPO_ML.json",
                parameter_path="pid.ki",
                delta=di,
                hard_limits={"min": ki_min, "max": ki_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.9, psi_conf),
                pattern="persistent_bias_integral_correction",
                signals={"psi": psi, "psi_conf": psi_conf, "trend_conf": trend_conf, "vol": vol},
                scope=scope,
                entity_id=entity_id
            ))

        return proposals

    # ------------------ builders ------------------

    def _proposal_delta(
        self,
        cfg_file: str,
        parameter_path: str,
        delta: float,
        hard_limits: Dict[str, float],
        max_delta: float,
        cooldown: str,
        confidence: float,
        pattern: str,
        signals: Dict[str, Any],
        scope: str,
        entity_id: str
    ) -> Dict[str, Any]:
        return {
            "metadata": {
                "proposal_id": _new_id(),
                "timestamp": _now(),
                "source_module": "cfg_pid_updater",
                "engine_version": "OSEngine",
                "environment": "prod"
            },
            "target": {
                "cfg_file": cfg_file,
                "scope": scope,
                "entity_id": entity_id,
                "parameter_path": parameter_path
            },
            "proposal": {
                "type": "delta",
                "delta": float(_clamp(delta, -max_delta, max_delta)),
                "direction": "increase" if delta > 0 else "decrease",
                "urgency": "low"
            },
            "justification": {
                "signals": signals,
                "pattern": pattern,
                "time_horizon": "structural"
            },
            "constraints": {
                "hard_limits": hard_limits,
                "max_delta": max_delta,
                "cooldown_period": cooldown,
                "max_frequency": "1_change_per_14d"
            },
            "confidence": {
                "proposal_confidence": float(_clamp(confidence, 0.0, 1.0)),
                "signal_consensus": float(_clamp((signals.get("psi_conf", 0.0) + signals.get("trend_conf", 0.0)) / 2.0, 0.0, 1.0)),
                "data_quality": float(_clamp(signals.get("psi_conf", 0.0), 0.0, 1.0))
            },
            "validation": {
                "requires_human_approval": False,
                "min_confidence_required": 0.70,
                "required_signals": ["psi", "trend"],
                "forbidden_conditions": ["active_shock"]
            },
            "audit": {
                "rollback_available": True
            }
        }

    def _proposal_freeze(
        self,
        cfg_file: str,
        parameter_path: str,
        reason: str,
        signals: Dict[str, Any],
        cooldown: str,
        scope: str,
        entity_id: str
    ) -> Dict[str, Any]:
        return {
            "metadata": {
                "proposal_id": _new_id(),
                "timestamp": _now(),
                "source_module": "cfg_pid_updater",
                "engine_version": "OSEngine",
                "environment": "prod"
            },
            "target": {
                "cfg_file": cfg_file,
                "scope": scope,
                "entity_id": entity_id,
                "parameter_path": parameter_path
            },
            "proposal": {
                "type": "freeze",
                "delta": 0.0,
                "direction": "hold",
                "urgency": "high"
            },
            "justification": {
                "signals": signals,
                "pattern": reason,
                "time_horizon": "transient"
            },
            "constraints": {
                "hard_limits": {"min": 0.0, "max": 1.0},
                "max_delta": 0.0,
                "cooldown_period": cooldown,
                "max_frequency": "1_change_per_14d"
            },
            "confidence": {
                "proposal_confidence": 0.9,
                "signal_consensus": 0.9,
                "data_quality": float(_clamp(signals.get("psi_conf", 0.0), 0.0, 1.0))
            },
            "validation": {
                "requires_human_approval": False,
                "min_confidence_required": 0.0,
                "required_signals": ["shock"],
                "forbidden_conditions": []
            },
            "audit": {
                "rollback_available": True
            }
        }
