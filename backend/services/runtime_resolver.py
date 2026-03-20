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
            "type": "multiplier_float",
            "min_multiplier": 0.80,  # Evita que un shock reduzca el margen a menos del 80%
            "max_multiplier": 1.20   # Evita subidas irreales de margen
        },
        {
            "param": "horizonte_meses",
            "source": "w_volatility",
            "rule": "volatility_horizon_extension",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int",
            "max_multiplier": 2.0  # El horizonte prospectivo no debería más que duplicarse
        }
    ],
    "SIGMA": [
        {
            "param": "costo_mantencion_pct",
            "source": "w_volatility",
            "rule": "volatility_cost_uplift",
            "min_val": 0.001,
            "max_val": 1.50,
            "type": "multiplier_float",
            "max_multiplier": 1.50
        },
        {
            "param": "costo_pedido",
            "source": "w_comex",
            "rule": "comex_cost_uplift",
            "min_val": 0.0,
            "max_val": 1_000_000_000.0,
            "type": "multiplier_float",
            "max_multiplier": 2.50
        },
        {
            "param": "costo_unitario",
            "source": "w_comex",
            "rule": "comex_unit_cost_uplift",
            "min_val": 0.0,
            "max_val": 1_000_000_000.0,
            "type": "multiplier_float",
            "max_multiplier": 2.0
        },
        {
            "param": "horizonte_meses",
            "source": "w_shock",
            "rule": "shock_horizon_adjustment",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int",
            "max_multiplier": 2.0
        }
    ],
    "POSEIDON": [
        {
            "param": "horizonte_meses",
            "source": "w_shock",
            "rule": "shock_horizon_adjustment",
            "min_val": 1.0,
            "max_val": 24.0,
            "type": "multiplier_int",
            "max_multiplier": 2.0
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

        # 1. Identificación de Gating Global (Sin retorno ciego)
        global_skip_reason = None
        if confidence_effective < min_conf:
            global_skip_reason = "insufficient_confidence"
            effective["_overlay_skipped"] = True
            effective["_overlay_reason"] = global_skip_reason
        elif not os_contract.is_ttl_valid():
            global_skip_reason = "expired_ttl"
            effective["_overlay_skipped"] = True
            effective["_overlay_reason"] = global_skip_reason

        # 2. Parameter Mapping & Trace Recording
        for rule_def in mappings:
            param = rule_def["param"]
            rule_name = rule_def["rule"]
            source_key = rule_def["source"]

            # Si el contrato fue bloqueado globalmente, registramos el rechazo explícito por regla
            if global_skip_reason:
                applied_patches.append({
                    "param": param,
                    "rule": rule_name,
                    "source": source_key,
                    "os_state": os_contract.os_state,
                    "applied": False,
                    "skip_reason": global_skip_reason
                })
                continue

            if param not in effective:
                applied_patches.append({
                    "param": param,
                    "rule": rule_name,
                    "source": source_key,
                    "os_state": os_contract.os_state,
                    "applied": False,
                    "skip_reason": "param_missing"
                })
                continue
            raw_multiplier = getattr(os_contract.runtime_context.multipliers, source_key, 1.0)
            
            # Extracción de guardrails específicos de la regla (con fallback a los globales)
            rule_min_mult = rule_def.get("min_multiplier", os_contract.runtime_context.guardrails.min_purchase_multiplier)
            rule_max_mult = rule_def.get("max_multiplier", os_contract.runtime_context.guardrails.max_purchase_multiplier)
            
            safe_multiplier = self._clamp_multiplier(
                raw_multiplier, 
                max_val=rule_max_mult,
                min_val=rule_min_mult
            )
            
            was_multiplier_clamped = (raw_multiplier != safe_multiplier)

            base_val = float(effective[param])
            final_type_cast = int if rule_def["type"] == "multiplier_int" else float

            if safe_multiplier != 1.0:
                new_val_float = base_val * safe_multiplier
                clamped_val = self._clamp_value(new_val_float, rule_def["min_val"], rule_def["max_val"])
                was_value_clamped = (new_val_float != clamped_val)
                
                final_val = final_type_cast(clamped_val)
                effective[param] = final_val
                
                applied_patches.append({
                    "param": param,
                    "base": final_type_cast(base_val),
                    "effective": final_val,
                    "multiplier": safe_multiplier,
                    "raw_multiplier": raw_multiplier,
                    "was_multiplier_clamped": was_multiplier_clamped,
                    "was_value_clamped": was_value_clamped,
                    "clamp_limits": {"min": rule_def["min_val"], "max": rule_def["max_val"]},
                    "rule_multiplier_limits": {"min": rule_min_mult, "max": rule_max_mult},
                    "source": source_key,
                    "confidence": confidence_effective,
                    "os_state": os_contract.os_state,
                    "rule": rule_name,
                    "applied": True
                })
            else:
                # Trazabilidad Neutral: Registro para el observatorio de reglas evaluadas pero sin efecto
                applied_patches.append({
                    "param": param,
                    "base": final_type_cast(base_val),
                    "effective": final_type_cast(base_val),
                    "multiplier": 1.0,
                    "raw_multiplier": raw_multiplier,
                    "was_multiplier_clamped": was_multiplier_clamped,
                    "was_value_clamped": False,
                    "clamp_limits": {"min": rule_def["min_val"], "max": rule_def["max_val"]},
                    "rule_multiplier_limits": {"min": rule_min_mult, "max": rule_max_mult},
                    "source": source_key,
                    "confidence": confidence_effective,
                    "os_state": os_contract.os_state,
                    "rule": rule_name,
                    "applied": False,
                    "skip_reason": "neutral_multiplier"
                })

        effective["_runtime_overlay"] = {
            "os_state": os_contract.os_state,
            "decision_mode": os_contract.decision_mode,
            "confidence_effective": confidence_effective,
            "applied_patches_count": sum(1 for patch in applied_patches if patch.get("applied") is True)
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
