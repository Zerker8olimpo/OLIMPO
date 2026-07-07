"""
Model Service Facade & Data Adapters
------------------------------------
Este módulo actúa exclusivamente como una fachada (Facade) para los routers HTTP.
Contiene las reglas de saneamiento de entrada (normalize) y adaptación de salida (adapt).
La orquestación de estado está delegada a `execution_pipeline.py` para mantener SRP.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException

from backend.api.schemas.model_io import (
    EpsilonOutput,
    ModelRunResponse,
    PoseidonOutput,
    SigmaOutput,
    WarningMessage,
)
from backend.digital_twin.helios_engine import HeliosEngine


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
            out.append(WarningMessage(code="MODEL_WARNING", message=str(item), severity="warning"))
    return out


def _model_dump(instance: Any) -> Dict[str, Any]:
    if hasattr(instance, "model_dump"):
        return instance.model_dump()
    return instance.dict()


def _model_validate(model_cls: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if hasattr(model_cls, "model_validate"):
            parsed = model_cls.model_validate(payload)
        else:
            parsed = model_cls.parse_obj(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MODEL_OUTPUT_CONTRACT_VIOLATION: {exc}") from exc
    return _model_dump(parsed)


def _sanitize_for_background(obj: Any, preserve_keys: tuple = (), current_key: str = "") -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize_for_background(v, preserve_keys, k) for k, v in obj.items()}
    elif isinstance(obj, list):
        if current_key in preserve_keys:
            return [_sanitize_for_background(i, preserve_keys) for i in obj]
        if len(obj) > 100:  # Truncar arrays masivos tipo Monte Carlo o simulaciones pesadas
            return f"<List truncated, length={len(obj)}>"
        return [_sanitize_for_background(i, preserve_keys) for i in obj]
    else:
        return obj


def _prepare_immutable_payload(payload: Dict[str, Any], preserve_keys: tuple = ()) -> Dict[str, Any]:
    try:
        sanitized = _sanitize_for_background(payload, preserve_keys)
        return json.loads(json.dumps(sanitized, default=str))
    except Exception as exc:
        return {"error": "serialization_failed", "details": str(exc)}


def _extract_interpretation(raw_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    interpretation = raw_result.get("interpretation")
    if interpretation is None:
        return None
    if isinstance(interpretation, dict):
        return interpretation
    return {"summary": str(interpretation)}


def _extract_horizon(model_name: str, raw_result: Dict[str, Any], model_output: Dict[str, Any]) -> int:
    explicit = raw_result.get("horizon")
    if explicit is not None:
        return _ensure_int(explicit, 0)
    if model_name == "EPSILON":
        return _ensure_int(model_output.get("horizonte_meses"), len(model_output.get("expected", [])))
    if model_name == "SIGMA":
        return _ensure_int(model_output.get("horizonte_meses"), len(model_output.get("demandDt", [])))
    if model_name == "POSEIDON":
        poseidon = model_output.get("poseidon", {})
        return _ensure_int(poseidon.get("horizonte_meses"), len(poseidon.get("poseidonInventario1", [])))
    return 0


def _normalize_epsilon_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)
    normalized["demanda_historica"] = _ensure_list(normalized.get("demanda_historica"))
    normalized["periodos"] = _ensure_int(normalized.get("periodos"), len(normalized["demanda_historica"]) or 12)
    normalized["margen_bruto_pct"] = _ensure_float(normalized.get("margen_bruto_pct"), 0.25)
    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")
    normalized["horizonte_meses"] = _ensure_int(normalized.get("horizonte_meses"), 3)
    normalized["activar_digital_twin"] = bool(normalized.get("activar_digital_twin", True))
    return normalized


def _normalize_sigma_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)
    normalized["demanda_historica"] = _ensure_list(normalized.get("demanda_historica"))
    normalized["periodos"] = _ensure_int(normalized.get("periodos"), len(normalized["demanda_historica"]) or 12)
    normalized["costo_unitario"] = _ensure_float(normalized.get("costo_unitario"), 0.0)
    normalized["costo_pedido"] = _ensure_float(normalized.get("costo_pedido"), 0.0)
    normalized["costo_mantencion_pct"] = _ensure_float(normalized.get("costo_mantencion_pct"), 0.0)
    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")
    normalized["horizonte_meses"] = _ensure_int(normalized.get("horizonte_meses"), 3)
    normalized["activar_digital_twin"] = bool(normalized.get("activar_digital_twin", True))
    return normalized


def _normalize_poseidon_input(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(params)
    demanda_hist = _ensure_list(normalized.get("demanda_historica"))
    normalized["demanda_historica"] = demanda_hist
    normalized["periodos"] = _ensure_int(normalized.get("periodos"), len(demanda_hist) or 12)
    normalized["product_id"] = str(normalized.get("product_id") or "")
    normalized["market_id"] = str(normalized.get("market_id") or "")
    normalized["pais_principal"] = str(normalized.get("pais_principal") or "")
    normalized["horizonte_meses"] = _ensure_int(normalized.get("horizonte_meses"), 6)
    normalized["activar_digital_twin"] = bool(normalized.get("activar_digital_twin", True))
    return normalized


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
    compra_sugerida_raw = raw.get("recommendedPurchase", raw.get("compra_sugerida"))
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


def _adapt_sigma(raw_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw_output or {}
    lead_time = _ensure_float(raw.get("leadTimeMeses"), _ensure_float(raw.get("lead_time_meses"), 0.0))
    nivel_servicio = _ensure_float(raw.get("nivelServicio"), _ensure_float(raw.get("nivel_servicio"), 0.0))
    adapted = {
        "demandDt": _ensure_list(raw.get("demandDt")),
        "eoqDt": _ensure_list(raw.get("eoqDt")),
        "ropDt": _ensure_list(raw.get("ropDt")),
        "leadTimeMeses": lead_time,
        "lead_time_meses": lead_time,
        "nivelServicio": nivel_servicio,
        "nivel_servicio": nivel_servicio,
        **{k: v for k, v in raw.items() if k not in ["leadTimeMeses", "lead_time_meses", "nivelServicio", "nivel_servicio"]},
    }
    return _model_validate(SigmaOutput, adapted)


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
            "demanda_proyectada": _ensure_list(poseidon_raw.get("demanda_proyectada")),
            "inventario_tanque1": _ensure_list(poseidon_raw.get("inventario_tanque1")),
            "inventario_tanque2": _ensure_list(poseidon_raw.get("inventario_tanque2")),
            "flujo_t1_t2": _ensure_list(poseidon_raw.get("flujo_t1_t2")),
            "produccion_sugerida": _ensure_list(poseidon_raw.get("produccion_sugerida")),
            "pid_params": poseidon_raw.get("pid_params") if isinstance(poseidon_raw.get("pid_params"), dict) else {},
            "kalman_params": poseidon_raw.get("kalman_params") if isinstance(poseidon_raw.get("kalman_params"), dict) else {},
        }
    }
    return _model_validate(PoseidonOutput, adapted)


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
        raise HTTPException(status_code=500, detail=f"MODEL_EXECUTION_FAILED: {exc}") from exc


def run_model_and_adapt(
    model_name: str,
    params: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user_context: Dict[str, Any]
) -> ModelRunResponse:
    """
    Punto de entrada orquestado de ejecución de modelos.
    Mantiene firma compatible abstrayendo el pipeline interno.
    """
    # Importación diferida (Lazy Import) para evitar dependencias circulares
    from backend.services.execution_pipeline import ModelExecutionPipeline

    pipeline = ModelExecutionPipeline(model_name, params)
    return pipeline.execute(background_tasks, user_context)
