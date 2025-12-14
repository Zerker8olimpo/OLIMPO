from datetime import datetime
from typing import Dict, Any, List
import uuid


def _now() -> str:
    return datetime.utcnow().isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


class StockUpdater:
    """
    StockUpdater (propuestas, no cambios)
    ------------------------------------
    Genera propuestas para parámetros de inventario:
    - ROP sensitivity
    - Safety stock multipliers
    - Buffers
    NO escribe CFG. NO emite órdenes.
    """

    def propose(
        self,
        analysis_results: Dict[str, Any],
        cfg_limits: Dict[str, Any],
        scope: str = "product",
        entity_id: str = "SKU_UNKNOWN"
    ) -> List[Dict[str, Any]]:

        psi = analysis_results.get("psi", {}).get("effective", 0.0)
        psi_conf = analysis_results.get("psi", {}).get("confidence", 0.0)
        vol = analysis_results.get("volatility", {}).get("sigma", {}).get("total", 0.0)
        shock_flag = analysis_results.get("shock", {}).get("shock_flag", 0)

        max_delta = float(cfg_limits.get("stock", {}).get("max_delta", 0.10))
        cooldown = cfg_limits.get("stock", {}).get("cooldown_period", "30d")
        min_conf_apply = float(cfg_limits.get("stock", {}).get("min_confidence_required", 0.70))

        ss_min = float(cfg_limits.get("stock", {}).get("ss_multiplier_min", 0.7))
        ss_max = float(cfg_limits.get("stock", {}).get("ss_multiplier_max", 1.3))

        proposals: List[Dict[str, Any]] = []

        if psi_conf < min_conf_apply:
            return proposals

        # Evitar cambios durante shock fuerte (o proponer freeze)
        if shock_flag and psi > float(cfg_limits.get("stock", {}).get("psi_shock_freeze", 0.8)):
            proposals.append(self._proposal_freeze(
                cfg_file="CFG_LIMITES_SUP_INF.json",
                parameter_path="stock.freeze",
                reason="shock_high_freeze_stock_tuning",
                signals={"psi": psi, "psi_conf": psi_conf, "vol": vol, "shock_flag": shock_flag},
                cooldown=cooldown,
                scope=scope,
                entity_id=entity_id
            ))
            return proposals

        # Heurística conservadora:
        # - si volatilidad alta o psi alto -> subir multiplicador safety stock levemente
        # - si estabilidad alta (vol baja y psi bajo) -> bajar muy levemente
        if vol > float(cfg_limits.get("stock", {}).get("volatility_high", 1.0)) or psi > 0.7:
            delta = _clamp(0.25 * max_delta, 0.0, max_delta)
            proposals.append(self._proposal_delta(
                cfg_file="CFG_LIMITES_SUP_INF.json",
                parameter_path="stock.safety_stock_multiplier",
                delta=delta,
                hard_limits={"min": ss_min, "max": ss_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.9, psi_conf),
                pattern="increase_buffer_high_uncertainty",
                signals={"psi": psi, "psi_conf": psi_conf, "vol": vol, "shock_flag": shock_flag},
                scope=scope,
                entity_id=entity_id
            ))
        elif vol < float(cfg_limits.get("stock", {}).get("volatility_low", 0.4)) and psi < 0.4:
            delta = -_clamp(0.10 * max_delta, 0.0, max_delta)
            proposals.append(self._proposal_delta(
                cfg_file="CFG_LIMITES_SUP_INF.json",
                parameter_path="stock.safety_stock_multiplier",
                delta=delta,
                hard_limits={"min": ss_min, "max": ss_max},
                max_delta=max_delta,
                cooldown=cooldown,
                confidence=min(0.85, psi_conf),
                pattern="decrease_buffer_stable_conditions",
                signals={"psi": psi, "psi_conf": psi_conf, "vol": vol, "shock_flag": shock_flag},
                scope=scope,
                entity_id=entity_id
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
        entity_id: str
    ) -> Dict[str, Any]:
        return {
            "metadata": {
                "proposal_id": _new_id(),
                "timestamp": _now(),
                "source_module": "cfg_stock_updater",
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
                "source_module": "cfg_stock_updater",
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
                "max_frequency": "1_change_per_30d"
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
