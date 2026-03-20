from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from backend.OSEngine.OSEngine_CORE import OSEngineCore

logger = logging.getLogger("olimpo.os_engine.runtime")


DEFAULT_CFG_BUNDLE: Dict[str, Any] = {
    "os": {
        "psi_warning": 0.35,
        "psi_stressed": 0.55,
        "psi_critical": 0.75,
        "min_confidence": 0.60,
    },
    "guardrails": {
        "min_confidence_to_act": 0.60,
        "max_purchase_multiplier": 2.50,
        "min_purchase_multiplier": 0.70,
    },
    "cfg_limits": {},
    "dispatchers": {},
}


DEFAULT_CONTRACT_VERSION = "OS_ENGINE_CONTRACT_1.1"
DEFAULT_TTL = {"unit": "hours", "value": 48}


@lru_cache(maxsize=1)
def _get_core() -> OSEngineCore:
    return OSEngineCore(cfg_bundle=DEFAULT_CFG_BUNDLE, ml_core=None, enable_scanners=False)


def _build_market_series(params: Dict[str, Any]) -> Optional[List[float]]:
    demanda = params.get("demanda_historica")
    if not isinstance(demanda, list) or len(demanda) < 3:
        return None
    try:
        values = [float(v) for v in demanda if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(values) < 3:
            return None
        mean = sum(values) / len(values)
        return [mean for _ in values]
    except Exception:
        return None


def _default_contract(model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    product_id = str(params.get("product_id") or "SKU_UNKNOWN")
    market_id = str(params.get("market_id") or "MARKET_UNKNOWN")
    country = str(params.get("pais_principal") or "Chile")
    return {
        "version": DEFAULT_CONTRACT_VERSION,
        "timestamp": "",
        "context": {
            "product_id": product_id,
            "market_id": market_id,
            "country": country,
            "timestamp": "",
        },
        "os_state": "STABLE",
        "decision_mode": "NORMAL",
        "rationale": {"reason": "shadow_default"},
        "confidence": {
            "effective": 0.0,
            "psi": 0.0,
            "trend": 0.0,
            "external_min": 0.0,
            "external_mean": 0.0,
        },
        "signals_summary": {
            "shock_flag": 0,
            "shock_intensity": 0.0,
            "volatility_band": "low",
            "volatility_total": 0.0,
            "trend_direction": "flat",
            "trend_strength": 0.0,
            "phi_value": 0.0,
            "psi_effective": 0.0,
            "external_quality": {"status": "disabled", "confidence_mean": 0.0, "confidence_min": 0.0},
        },
        "ttl": dict(DEFAULT_TTL),
        "overlay_trace": {
            "scope": {"product_id": product_id, "market_id": market_id, "country": country},
            "decision_mode": "NORMAL",
            "os_state": "STABLE",
            "multipliers": {"w_shock": 1.0, "w_volatility": 1.0, "w_comex": 1.0, "elasticity": 1.0},
            "flags": {"freeze_tuning": False, "active_shock": False},
            "guardrails": DEFAULT_CFG_BUNDLE["guardrails"],
            "confidence_effective": 0.0,
            "ttl": dict(DEFAULT_TTL),
        },
        "analysis_results": {},
        "runtime_context": {
            "multipliers": {"w_shock": 1.0, "w_volatility": 1.0, "w_comex": 1.0, "elasticity": 1.0},
            "guardrails": dict(DEFAULT_CFG_BUNDLE["guardrails"]),
            "flags": {"freeze_tuning": False, "active_shock": False},
        },
        "proposals": [],
        "external_signals": {"status": "disabled", "confidence_mean": 0.0, "confidence_min": 0.0},
        "dispatch": {},
        "shadow_mode": True,
        "shadow_status": "default",
        "model_name": model_name,
    }


def _normalize_contract(contract: Optional[Dict[str, Any]], model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _default_contract(model_name, params)
    if not isinstance(contract, dict):
        normalized["shadow_status"] = "fallback_non_dict"
        return normalized

    normalized.update({
        "version": str(contract.get("version") or normalized["version"]),
        "timestamp": str(contract.get("timestamp") or normalized["timestamp"]),
        "os_state": str(contract.get("os_state") or normalized["os_state"]),
        "decision_mode": str(contract.get("decision_mode") or normalized["decision_mode"]),
        "rationale": contract.get("rationale") or normalized["rationale"],
        "confidence": contract.get("confidence") or normalized["confidence"],
        "signals_summary": contract.get("signals_summary") or normalized["signals_summary"],
        "ttl": contract.get("ttl") or normalized["ttl"],
        "overlay_trace": contract.get("overlay_trace") or normalized["overlay_trace"],
        "analysis_results": contract.get("analysis_results") or normalized["analysis_results"],
        "runtime_context": contract.get("runtime_context") or normalized["runtime_context"],
        "proposals": contract.get("proposals") or normalized["proposals"],
        "external_signals": contract.get("external_signals") or normalized["external_signals"],
        "dispatch": contract.get("dispatch") or normalized["dispatch"],
        "context": contract.get("context") or normalized["context"],
    })
    normalized["shadow_mode"] = True
    normalized["shadow_status"] = "ok"
    normalized["model_name"] = model_name
    return normalized


def evaluate_shadow(model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    default_contract = _default_contract(model_name, params)
    try:
        demanda = params.get("demanda_historica") or []
        product_series = [float(v) for v in demanda if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(product_series) < 3:
            default_contract["shadow_status"] = "insufficient_series"
            return default_contract

        context = {
            "product_id": str(params.get("product_id") or "SKU_UNKNOWN"),
            "market_id": str(params.get("market_id") or "MARKET_UNKNOWN"),
            "country": str(params.get("pais_principal") or "Chile"),
            "model_name": model_name,
        }

        contract = _get_core().tick(
            context=context,
            product_series=product_series,
            market_series=_build_market_series(params),
            helios_results=None,
        )
        return _normalize_contract(contract, model_name, params)
    except Exception as exc:
        logger.warning("[OS_ENGINE] Shadow mode fallback: %s", exc, exc_info=True)
        default_contract["shadow_status"] = "fallback_exception"
        default_contract["rationale"] = {"reason": "shadow_exception", "error": str(exc)}
        return default_contract
