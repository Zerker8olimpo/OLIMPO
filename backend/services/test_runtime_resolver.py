import pytest
from unittest.mock import patch

from backend.services.runtime_resolver import runtime_resolver
from backend.contracts.os_contract import (
    OSContract,
    Confidence,
    Guardrails,
    Multipliers,
    RuntimeContext
)


def create_mock_contract(
    confidence_eff: float = 1.0,
    min_conf: float = 0.6,
    w_shock: float = 1.0,
    w_volatility: float = 1.0
) -> OSContract:
    """Helper para generar un contrato determinista para los tests."""
    return OSContract(
        confidence=Confidence(effective=confidence_eff),
        runtime_context=RuntimeContext(
            guardrails=Guardrails(
                min_confidence_to_act=min_conf,
                min_purchase_multiplier=0.5,
                max_purchase_multiplier=2.5
            ),
            multipliers=Multipliers(
                w_shock=w_shock,
                w_volatility=w_volatility
            )
        )
    )


def test_global_skip_insufficient_confidence():
    """Valida que si la confianza es menor al límite, se omita globalmente la evaluación."""
    contract = create_mock_contract(confidence_eff=0.5, min_conf=0.6)
    inputs = {"margen_bruto_pct": 0.25}  # Parámetro mapeado para EPSILON

    effective, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    assert effective.get("_overlay_skipped") is True
    assert effective.get("_overlay_reason") == "insufficient_confidence"
    assert effective["_runtime_overlay"]["applied_patches_count"] == 0

    # Verificamos que el rastro de la regla registre el skip_reason explícito
    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is False
    assert patch_trace["skip_reason"] == "insufficient_confidence"


@patch.object(OSContract, "is_ttl_valid", return_value=False)
def test_global_skip_expired_ttl(mock_ttl_valid):
    """Valida que un contrato con TTL expirado bloquee la mutación y deje huella."""
    contract = create_mock_contract(confidence_eff=1.0)
    inputs = {"margen_bruto_pct": 0.25}

    effective, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    assert effective.get("_overlay_skipped") is True
    assert effective.get("_overlay_reason") == "expired_ttl"
    
    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is False
    assert patch_trace["skip_reason"] == "expired_ttl"


def test_param_missing_trace():
    """Valida que si un input no se envió, la regla declarativa deje rastro de param_missing."""
    contract = create_mock_contract(confidence_eff=1.0)
    inputs = {"horizonte_meses": 6} # Omitimos 'margen_bruto_pct' deliberadamente

    _, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is False
    assert patch_trace["skip_reason"] == "param_missing"


def test_neutral_multiplier_trace():
    """Valida que si el motor devuelve 1.0 (estado estable), no muta pero deja rastro neutral."""
    contract = create_mock_contract(confidence_eff=1.0, w_shock=1.0)
    inputs = {"margen_bruto_pct": 0.25}

    effective, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    assert effective["margen_bruto_pct"] == 0.25  # El valor base no fue alterado
    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is False
    assert patch_trace["skip_reason"] == "neutral_multiplier"
    assert patch_trace["was_multiplier_clamped"] is False
    assert effective["_runtime_overlay"]["applied_patches_count"] == 0


def test_was_multiplier_clamped():
    """Valida que un multiplicador extremo (1.5) sea capado por los límites específicos de la regla (1.20)."""
    contract = create_mock_contract(confidence_eff=1.0, w_shock=1.5)
    inputs = {"margen_bruto_pct": 0.25}

    effective, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is True
    assert patch_trace["raw_multiplier"] == 1.5
    assert patch_trace["multiplier"] == 1.2  # Clamp activado por la regla declarativa max_multiplier=1.20
    assert patch_trace["was_multiplier_clamped"] is True
    assert effective["_runtime_overlay"]["applied_patches_count"] == 1


def test_was_value_clamped():
    """Valida que si el valor matemático resultante excede el máximo permitido de la regla (0.99), este se restrinja."""
    contract = create_mock_contract(confidence_eff=1.0, w_shock=1.2)
    inputs = {"margen_bruto_pct": 0.90} # 0.90 * 1.20 = 1.08. Supera el max_val: 0.99

    effective, patches = runtime_resolver.resolve_model_inputs(
        model_name="EPSILON", base_inputs=inputs, os_contract=contract
    )

    patch_trace = next(p for p in patches if p["param"] == "margen_bruto_pct")
    assert patch_trace["applied"] is True
    assert patch_trace["was_value_clamped"] is True
    assert patch_trace["effective"] == 0.99
    assert effective["margen_bruto_pct"] == 0.99