from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from backend.api.schemas.model_io import (
    EpsilonOutput,
    ModelRunResponse,
    PoseidonOutput,
    SigmaOutput,
    WarningMessage,
)
from backend.core.contracts.input_validator import validate_model_input
from backend.digital_twin.helios_engine import HeliosEngine


# =========================================================
# Defensive helpers
# =========================================================

def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _ensure_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ensure_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_last(values: List[Any], default: float = 0.0) -> float:
    if not values:
        return default
    try:
        return float(values[-1])
    except (TypeError, ValueError):
        return default


# =========================================================
# Warning coercion
# =========================================================

def _coerce_warnings(raw_warnings: Any) -> List[WarningMessage]:
    if not isinstance(raw_warnings, list):
        return []

    out: List[WarningMessage] = []

    for item in raw_warnings:
        if isinstance(item, dict):
            out.append(
                WarningMessage(
                    code=str(item.get("code") or "MODEL_WARNING"),
                    message=str(item.get("message") or "Warning emitted by model"),
                    field=item.get("field"),
                    severity=str(item.get("severity") or "warning"),
                )
            )
        else:
            out.append(
                WarningMessage(
                    code="MODEL_WARNING",
                    message=str(item),
                    severity="warning",
                )
            )

    return out


# =========================================================
# Pydantic compatibility
# =========================================================

def _model_dump(instance: Any) -> Dict[str, Any]:
    if hasattr(instance, "dict"):
        return instance.dict()

    return instance.model_dump()


def _model_validate(model_cls: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if hasattr(model_cls, "parse_obj"):
            parsed = model_cls.parse_obj(payload)
        else:
            parsed = model_cls.model_validate(payload)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MODEL_OUTPUT_CONTRACT_VIOLATION: {exc}",
        ) from exc

    return _model_dump(parsed)


# =========================================================
# Interpretation
# =========================================================

def _extract_interpretation(raw_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    interpretation = raw_result.get("interpretation")

    if interpretation is None:
        return None

    if isinstance(interpretation, dict):
        return interpretation

    return {"summary": str(interpretation)}


# =========================================================
# Horizon extractor
# =========================================================

def _extract_horizon(model_name: str, raw_result: Dict[str, Any], model_output: Dict[str, Any]) -> int:
    explicit = raw_result.get("horizon")

    if explicit is not None:
        return _ensure_int(explicit, 0)

    if model_name == "EPSILON":
        return _ensure_int(
            model_output.get("horizonte_meses"),
            len(model_output.get("expected", [])),
        )

    if model_name == "SIGMA":
        return _ensure_int(
            model_output.get("horizonte_meses"),
            len(model_output.get("demandDt", [])),
        )

    if model_name == "POSEIDON":
        poseidon = model_output.get("poseidon", {})
        return _ensure_int(
            poseidon.get("horizonte_meses"),
            len(poseidon.get("poseidonInventario1", [])),
        )

    return 0


# =========================================================
# Input normalization
# =========================================================

def _normalize_epsilon_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)

    normalized["demanda_historica"] = _ensure_list(normalized.get("demanda_historica"))
    normalized["periodos"] = _ensure_int(
        normalized.get("periodos"),
        len(normalized["demanda_historica"]) or 12,
    )
    normalized["margen_bruto_pct"] = _ensure_float(
        normalized.get("margen_bruto_pct"),
        0.25,
    )

    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")

    normalized["horizonte_meses"] = _ensure_int(
        normalized.get("horizonte_meses"),
        3,
    )

    normalized["activar_digital_twin"] = bool(
        normalized.get("activar_digital_twin", True)
    )

    return normalized


def _normalize_sigma_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)

    normalized["demanda_historica"] = _ensure_list(normalized.get("demanda_historica"))
    normalized["periodos"] = _ensure_int(
        normalized.get("periodos"),
        len(normalized["demanda_historica"]) or 12,
    )

    normalized["costo_unitario"] = _ensure_float(
        normalized.get("costo_unitario"),
        0.0,
    )
    normalized["costo_pedido"] = _ensure_float(
        normalized.get("costo_pedido"),
        0.0,
    )
    normalized["costo_mantencion_pct"] = _ensure_float(
        normalized.get("costo_mantencion_pct"),
        0.0,
    )

    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")

    normalized["horizonte_meses"] = _ensure_int(
        normalized.get("horizonte_meses"),
        3,
    )

    normalized["activar_digital_twin"] = bool(
        normalized.get("activar_digital_twin", True)
    )

    return normalized


def _normalize_poseidon_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)

    demanda_hist = _ensure_list(normalized.get("demanda_historica"))

    normalized["demanda_historica"] = demanda_hist
    normalized["periodos"] = _ensure_int(
        normalized.get("periodos"),
        len(demanda_hist) or 12,
    )

    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")

    normalized["horizonte_meses"] = _ensure_int(
        normalized.get("horizonte_meses"),
        6,
    )
    normalized["activar_digital_twin"] = bool(
        normalized.get("activar_digital_twin", True)
    )

    return normalized


# =========================================================
# EPSILON adapter (ROBUST)
# =========================================================

def _adapt_epsilon(raw_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw_output or {}

    p50 = _ensure_list(raw.get("p50"))
    p95 = _ensure_list(raw.get("p95"))

    if p50 and p95:
        min_len = min(len(p50), len(p95))
        p50 = p50[:min_len]
        p95 = p95[:min_len]

    lower_raw = raw.get("lower")

    if isinstance(lower_raw, list):
        lower = _ensure_list(lower_raw)[:len(p50)]
    else:
        lower = []
        for m, u in zip(p50, p95):
            try:
                lower.append(max(0.0, (2 * float(m)) - float(u)))
            except (TypeError, ValueError):
                lower.append(0.0)

    compra_sugerida_raw = raw.get(
        "recommendedPurchase",
        raw.get("compra_sugerida"),
    )

    compra_sugerida_val = _ensure_list(compra_sugerida_raw)
    recommended_purchase_val = _safe_last(compra_sugerida_val, 0.0)

    adapted = {
        "expected": _ensure_list(raw.get("expected")) or p50,
        "smooth": _ensure_list(raw.get("smooth")) or p50,
        "stress": _ensure_list(raw.get("stress")) or p95,
        "upper": _ensure_list(raw.get("upper")) or p95,
        "lower": lower,
        "p50": p50,
        "p95": p95,
        "recommendedPurchase": recommended_purchase_val,
        "compra_sugerida": compra_sugerida_val,
        "volatilityIndex": _ensure_float(raw.get("volatilityIndex"), 0.0),
        "confidenceIndex": _ensure_float(raw.get("confidenceIndex"), 0.0),
        "stability": _ensure_float(raw.get("stability"), 0.0),
        "product_id": raw.get("product_id"),
        "market_id": raw.get("market_id"),
        "horizonte_meses": _ensure_int(raw.get("horizonte_meses"), len(p50)),
    }

    return _model_validate(EpsilonOutput, adapted)


# =========================================================
# SIGMA adapter
# =========================================================

def _adapt_sigma(raw_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw_output or {}

    lead_time = _ensure_float(
        raw.get("leadTimeMeses"),
        _ensure_float(raw.get("lead_time_meses"), 0.0),
    )
    nivel_servicio = _ensure_float(
        raw.get("nivelServicio"),
        _ensure_float(raw.get("nivel_servicio"), 0.0),
    )

    adapted = {
        "demandDt": _ensure_list(raw.get("demandDt")),
        "eoqDt": _ensure_list(raw.get("eoqDt")),
        "ropDt": _ensure_list(raw.get("ropDt")),
        "leadTimeMeses": lead_time,
        "lead_time_meses": lead_time,
        "nivelServicio": nivel_servicio,
        "nivel_servicio": nivel_servicio,
        # Copiar el resto de los campos para validación
        **{k: v for k, v in raw.items() if k not in ["leadTimeMeses", "lead_time_meses", "nivelServicio", "nivel_servicio"]}
    }

    return _model_validate(SigmaOutput, adapted)


# =========================================================
# POSEIDON adapter
# =========================================================

def _adapt_poseidon(raw_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw_output or {}

    poseidon_raw = raw.get("poseidon") if isinstance(raw.get("poseidon"), dict) else raw

    adapted = {
        "poseidon": {
            "poseidonInventario1": _ensure_list(poseidon_raw.get("poseidonInventario1")),
            "poseidonInventario2": _ensure_list(poseidon_raw.get("poseidonInventario2")),
            "poseidonFlujo": _ensure_list(poseidon_raw.get("poseidonFlujo")),
            "product_id": poseidon_raw.get("product_id"),
            "market_id": poseidon_raw.get("market_id"),
            "horizonte_meses": _ensure_int(
                poseidon_raw.get("horizonte_meses"),
                len(_ensure_list(poseidon_raw.get("poseidonInventario1"))),
            ),
        }
    }

    return _model_validate(PoseidonOutput, adapted)


# =========================================================
# HELIOS call
# =========================================================

def _call_helios(engine: HeliosEngine, model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    model_key = model_name.upper().strip()

    try:
        if model_key == "EPSILON":
            return engine.run_epsilon(params)

        if model_key == "SIGMA":
            return engine.run_sigma(params)

        if model_key == "POSEIDON":
            return engine.run_poseidon(params)

        raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MODEL_EXECUTION_FAILED: {exc}",
        ) from exc


# =========================================================
# MAIN ENTRYPOINT
# =========================================================

def run_model_and_adapt(model_name: str, params: Dict[str, Any]) -> ModelRunResponse:
    model_key = model_name.upper().strip()

    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="Invalid params payload")

    # -----------------------------------------------------
    # VALIDATE RAW INPUT AGAINST CANONICAL CONTRACT
    # Must happen BEFORE normalization, otherwise defaults
    # can hide missing required fields.
    # -----------------------------------------------------
    try:
        validate_model_input(model_key, params)
    except ValueError as exc:
        detail = exc.args[0] if exc.args else {"error": "INVALID_INPUT", "model": model_key}
        raise HTTPException(status_code=422, detail=detail) from exc

    if model_key == "EPSILON":
        normalized_params = _normalize_epsilon_input(params)

    elif model_key == "SIGMA":
        normalized_params = _normalize_sigma_input(params)

    elif model_key == "POSEIDON":
        normalized_params = _normalize_poseidon_input(params)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

    engine = HeliosEngine(enable_logs=False)

    raw_result = _call_helios(engine, model_key, normalized_params)

    if raw_result is None:
        raise HTTPException(
            status_code=500,
            detail="MODEL_EXECUTION_FAILED: HELIOS returned null",
        )

    if not isinstance(raw_result, dict):
        raise HTTPException(
            status_code=500,
            detail="MODEL_EXECUTION_FAILED: HELIOS result invalid",
        )

    if model_key == "EPSILON":
        adapted_output = _adapt_epsilon(raw_result)

    elif model_key == "SIGMA":
        adapted_output = _adapt_sigma(raw_result)

    else:
        adapted_output = _adapt_poseidon(raw_result)

    response_payload = {
        "modelName": model_key,
        "horizon": _extract_horizon(model_key, raw_result, adapted_output),
        "interpretation": _extract_interpretation(raw_result),
        "warnings": [_model_dump(w) for w in _coerce_warnings(raw_result.get("warnings"))],
        "modelOutput": adapted_output,
    }

    try:
        if hasattr(ModelRunResponse, "parse_obj"):
            return ModelRunResponse.parse_obj(response_payload)

        return ModelRunResponse.model_validate(response_payload)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MODEL_RESPONSE_CONTRACT_VIOLATION: {exc}",
        ) from exc