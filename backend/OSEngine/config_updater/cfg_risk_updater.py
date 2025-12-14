from datetime import datetime
from typing import Dict, Any, List
import uuid


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


class RiskUpdater:
    """
    RiskUpdater (propuestas, no cambios)
    -----------------------------------
    Ajusta parámetros de tolerancia/umbrales de riesgo vía propuestas.
    NO escribe CFG.
    """

    def propose(
        self,
        analysis_results: Dict[str, Any],
        cfg_limits: Dict[str, Any],
        scope: str = "market",
        entity_id: str = "MARKET_UNKNOWN",
    ) -> List[Dict[str, Any]]:

        psi = analysis_results.get("psi", {}).get("effective", 0.0)
        psi_conf = analysis_results.get("psi", {}).get("confidence", 0.0)
        vol = analysis_results.get("volatility", {}).get("sigma", {}).get("total", 0.0)
        shock_flag = analysis_results.get("shock", {}).get("shock_flag", 0)

        max_delta = float(cfg_limits.get("risk", {}).get("max_delta", 0.05))
        cooldown = cfg_limits.get("risk", {}).get("cooldown_period", "30d")
        min_conf_apply = float(cfg_limits.get("risk", {}).get("min_confidence_required", 0.70))

        thr_min = float(cfg_limits.get("risk", {}).get("threshold_min", 0.1))
        thr_max = float(cfg_limits.get("risk", {}).get("threshold_max", 1.0))

        proposals: List[Dict[str, Any]] = []

        if psi_conf < min_conf_apply:
            return proposals

        # Idea: si el sistema está muy volátil, endurecer umbrales (más conservador)
        # si está estable y psi bajo, relajar levemente (menos falsos positivos)
        if shock_flag or vol > float(cfg_limits.get("risk", {}).get("volatility_high", 1.0)) or psi > 0.7:
            # endurecer: bajar threshold de alerta -> detecta antes (o subir “tolerancia” según tu CFG)
            # como no sabemos tu ruta exacta aún, usamos un ejemplo de parameter_path permitido
            proposals.append(self._proposal_delta(
                cfg_file="CFG_LIMITES_SUP_INF.json",
                parameter_path="risk.threshold_alert",
                delta=-_clamp(0.5 * max_delta, 0.0, max_delta),
                hard_limits={"min": thr_min, "max": thr_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.9, psi_conf),
                pattern="risk_harden_high_vol_or_shock",
                signals={"psi": psi, "psi_conf": psi_conf, "vol": vol, "shock_flag": shock_flag},
                scope=scope,
                entity_id=entity_id,
                forbidden=["active_shock"]  # si quieres permitir en shock, se elimina aquí
            ))
        elif vol < float(cfg_limits.get("risk", {}).get("volatility_low", 0.4)) and psi < 0.4:
            proposals.append(self._proposal_delta(
                cfg_file="CFG_LIMITES_SUP_INF.json",
                parameter_path="risk.threshold_alert",
                delta=_clamp(0.25 * max_delta, 0.0, max_delta),
                hard_limits={"min": thr_min, "max": thr_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.85, psi_conf),
                pattern="risk_relax_stable_conditions",
                signals={"psi": psi, "psi_conf": psi_conf, "vol": vol, "shock_flag": shock_flag},
                scope=scope,
                entity_id=entity_id,
                forbidden=["active_shock"]
            ))

        return proposals

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
        entity_id: str,
        forbidden: List[str],
    ) -> Dict[str, Any]:
        return {
            "metadata": {
                "proposal_id": _new_id(),
                "timestamp": _now(),
                "source_module": "cfg_risk_updater",
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
                "max_frequency": "1_change_per_30d"
            },
            "confidence": {
                "proposal_confidence": float(_clamp(confidence, 0.0, 1.0)),
                "signal_consensus": float(_clamp((signals.get("psi_conf", 0.0) + (1.0 if signals.get("vol", 0.0) > 0 else 0.0)) / 2.0, 0.0, 1.0)),
                "data_quality": float(_clamp(signals.get("psi_conf", 0.0), 0.0, 1.0))
            },
            "validation": {
                "requires_human_approval": False,
                "min_confidence_required": 0.70,
                "required_signals": ["psi", "volatility"],
                "forbidden_conditions": forbidden
            },
            "audit": {
                "rollback_available": True
            }
        }
