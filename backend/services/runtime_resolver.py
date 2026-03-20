from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple, Optional

from backend.contracts.os_contract import OSContract


# Mapping Declarativo: Aísla las reglas de negocio del motor del resolver.
# Previene el crecimiento descontrolado de lógica hardcodeada ("God Object").
PARAMETER_MAPPING = {
    "EPSILON": [
        {
            "param": "margen_bruto_pct",
            "source": "w_shock",
            "rule": "shock_margin_adjustment",
            "min_val": 0.01,
            "max_val": 0.99,
            "type": "multiplier_float"
        },
        {
            "param": "horizonte_meses",
            "source": "w_volatility",
            "rule": "volatility_horizon_extension",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int"
        }
    ],
    "SIGMA": [
        {
            "param": "costo_mantencion_pct",
            "source": "w_volatility",
            "rule": "volatility_cost_uplift",
            "min_val": 0.001,
            "max_val": 1.50,
            "type": "multiplier_float"
        },
        {
            "param": "costo_pedido",
            "source": "w_comex",
            "rule": "comex_cost_uplift",
            "min_val": 0.0,
            "max_val": 1_000_000_000.0,
            "type": "multiplier_float"
        },
        {
            "param": "costo_unitario",
            "source": "w_comex",
            "rule": "comex_unit_cost_uplift",
            "min_val": 0.0,
            "max_val": 1_000_000_000.0,
            "type": "multiplier_float"
        },
        {
            "param": "horizonte_meses",
            "source": "w_shock",
            "rule": "shock_horizon_adjustment",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int"
        }
    ],
    "POSEIDON": [
        {
            "param": "horizonte_meses",
            "source": "w_shock",
            "rule": "shock_horizon_adjustment",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int"
        }
    ]
}


class RuntimeResolver:
    def resolve_model_inputs(
        self,
        *,
        model_name: str,
        base_inputs: Dict[str, Any],
        os_contract: Optional[OSContract],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        effective = copy.deepcopy(base_inputs)
        applied_patches: List[Dict[str, Any]] = []

        if not os_contract:
            return effective, applied_patches

        model_key = model_name.upper().strip()
        mappings = PARAMETER_MAPPING.get(model_key, [])
        if not mappings:
            return effective, applied_patches

        confidence_effective = os_contract.effective_confidence
        min_conf = os_contract.runtime_context.guardrails.min_confidence_to_act

        # 1. Confidence Gating
        if confidence_effective < min_conf:
            effective["_overlay_skipped"] = True
            effective["_overlay_reason"] = "insufficient_confidence"
            return effective, applied_patches

        # 2. TTL Awareness
        if not os_contract.is_ttl_valid():
            effective["_overlay_skipped"] = True
            effective["_overlay_reason"] = "expired_ttl"
            return effective, applied_patches

        # 3. Parameter Mapping & Patch Injection
        for rule_def in mappings:
            param = rule_def["param"]
            if param not in effective:
                continue

            source_key = rule_def["source"]
            raw_multiplier = getattr(os_contract.runtime_context.multipliers, source_key, 1.0)
            
            safe_multiplier = self._clamp_multiplier(
                raw_multiplier, 
                max_val=os_contract.runtime_context.guardrails.max_purchase_multiplier,
                min_val=os_contract.runtime_context.guardrails.min_purchase_multiplier
            )

            if safe_multiplier != 1.0:
                base_val = float(effective[param])
                new_val_float = base_val * safe_multiplier
                clamped_val = self._clamp_value(new_val_float, rule_def["min_val"], rule_def["max_val"])
                
                final_val = int(clamped_val) if rule_def["type"] == "multiplier_int" else clamped_val
                effective[param] = final_val
                
                applied_patches.append({
                    "param": param,
                    "base": int(base_val) if rule_def["type"] == "multiplier_int" else base_val,
                    "effective": final_val,
                    "multiplier": safe_multiplier,
                    "clamp_limits": {"min": rule_def["min_val"], "max": rule_def["max_val"]},
                    "source": source_key,
                    "confidence": confidence_effective,
                    "os_state": os_contract.os_state,
                    "rule": rule_def["rule"],
                    "applied": True
                })

        effective["_runtime_overlay"] = {
            "os_state": os_contract.os_state,
            "decision_mode": os_contract.decision_mode,
            "confidence_effective": confidence_effective,
            "applied_patches_count": len(applied_patches)
        }
        return effective, applied_patches

    def _clamp_multiplier(self, value: Any, max_val: float, min_val: float) -> float:
        try:
            fv = float(value)
        except Exception:
            fv = 1.0
        return max(min_val, min(max_val, fv))

    def _clamp_value(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, float(value)))


runtime_resolver = RuntimeResolver()
