from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, HTTPException

from backend.api.schemas.model_io import ModelRunResponse
from backend.contracts.os_contract import OSContract
from backend.core.contracts.input_validator import validate_model_input
from backend.digital_twin.helios_engine import HeliosEngine
from backend.observatory.services.observatory_service import observatory_service
from backend.services.os_engine_runtime import evaluate_shadow
from backend.services.runtime_resolver import runtime_resolver
from backend.observatory.services.runtime_trace import RuntimeTrace

# Importamos helpers y adaptadores del dominio desde la fachada model_service
from backend.services.model_service import (
    _normalize_epsilon_input,
    _normalize_sigma_input,
    _normalize_poseidon_input,
    _call_helios,
    _adapt_epsilon,
    _adapt_sigma,
    _adapt_poseidon,
    _coerce_warnings,
    _model_dump,
    _prepare_immutable_payload,
    _extract_horizon,
    _extract_interpretation,
)

logger = logging.getLogger("olimpo.pipeline")


class ModelExecutionPipeline:
    """
    Pipeline orquestador para la ejecución segura e inmutable de modelos.
    Aplica patrón Pipeline para aislar responsabilidades (SRP).
    """
    def __init__(self, model_name: str, params: Dict[str, Any]):
        self.model_name = model_name.upper().strip()
        self.raw_params = params
        self.normalized_params: Dict[str, Any] = {}
        self.os_contract: Optional[OSContract] = None
        self.effective_params: Dict[str, Any] = {}
        self.raw_result: Dict[str, Any] = {}
        self.adapted_output: Dict[str, Any] = {}
        self.applied_patches: List[Dict[str, Any]] = []
        self.runtime_trace: Optional[RuntimeTrace] = None

    def execute(self, background_tasks: BackgroundTasks, user_context: Dict[str, Any]) -> ModelRunResponse:
        logger.info("[PIPELINE] Iniciando ejecución orquestada para modelo: %s", self.model_name)
        self._validate_input()
        self._normalize_input()
        self._evaluate_os_engine_shadow()
        self._resolve_runtime_context()
        self._execute_primary_model_and_enrich()
        self._apply_output_guards()
        self._stamp_runtime_trace()
        self._dispatch_observatory_async(background_tasks, user_context)
        logger.info("[PIPELINE] Ejecución completada exitosamente: %s", self.model_name)
        return self._build_response()

    def _validate_input(self) -> None:
        if not isinstance(self.raw_params, dict):
            raise HTTPException(status_code=400, detail="Invalid params payload")
        try:
            validate_model_input(self.model_name, self.raw_params)
        except ValueError as exc:
            detail = exc.args[0] if exc.args else {"error": "INVALID_INPUT", "model": self.model_name}
            raise HTTPException(status_code=422, detail=detail) from exc

    def _normalize_input(self) -> None:
        if self.model_name == "EPSILON":
            self.normalized_params = _normalize_epsilon_input(self.raw_params)
        elif self.model_name == "SIGMA":
            self.normalized_params = _normalize_sigma_input(self.raw_params)
        elif self.model_name == "POSEIDON":
            self.normalized_params = _normalize_poseidon_input(self.raw_params)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {self.model_name}")

    def _evaluate_os_engine_shadow(self) -> None:
        raw_contract = evaluate_shadow(self.model_name, self.normalized_params)
        try:
            self.os_contract = OSContract.model_validate(raw_contract)
        except Exception as exc:
            logger.warning("[PIPELINE] Error validando OSContract crudo: %s", exc)
            self.os_contract = OSContract(shadow_status="contract_validation_failed")

    def _resolve_runtime_context(self) -> None:
        self.effective_params, self.applied_patches = runtime_resolver.resolve_model_inputs(
            model_name=self.model_name,
            base_inputs=self.normalized_params,
            os_contract=self.os_contract,
        )

    def _execute_primary_model_and_enrich(self) -> None:
        engine = HeliosEngine(enable_logs=False)
        self.raw_result = _call_helios(engine, self.model_name, self.effective_params)
        if self.raw_result is None:
            raise HTTPException(status_code=500, detail="MODEL_EXECUTION_FAILED: HELIOS returned null")
        if not isinstance(self.raw_result, dict):
            raise HTTPException(status_code=500, detail="MODEL_EXECUTION_FAILED: HELIOS result invalid")

    def _apply_output_guards(self) -> None:
        if self.model_name == "EPSILON":
            self.adapted_output = _adapt_epsilon(self.raw_result)
        elif self.model_name == "SIGMA":
            self.adapted_output = _adapt_sigma(self.raw_result)
        else:
            self.adapted_output = _adapt_poseidon(self.raw_result)

    def _stamp_runtime_trace(self) -> None:
        if self.os_contract:
            os_state = self.os_contract.os_state
            decision_mode = self.os_contract.decision_mode
            confidence_val = self.os_contract.effective_confidence
            shadow_status = self.os_contract.shadow_status
            signals_summary = self.os_contract.signals_summary
            overlay_trace = self.os_contract.overlay_trace
            ttl = self.os_contract.ttl.model_dump()
        else:
            os_state = "UNKNOWN"
            decision_mode = "UNKNOWN"
            confidence_val = 0.0
            shadow_status = "UNKNOWN"
            signals_summary = {}
            overlay_trace = {}
            ttl = {}

        self.runtime_trace = RuntimeTrace(
            model_name=self.model_name,
            os_state=os_state,
            decision_mode=decision_mode,
            confidence=confidence_val,
            shadow_status=shadow_status,
            runtime_context_summary=signals_summary,
            overlay_trace=overlay_trace,
            ttl=ttl,
            helios_enriched=True,
            resolver_applied=bool(self.applied_patches),
            applied_patches=self.applied_patches
        )

    def _dispatch_observatory_async(self, background_tasks: BackgroundTasks, user_context: Dict[str, Any]) -> None:
        obs_context = _model_dump(self.runtime_trace) if self.runtime_trace else {}
        obs_context["helios_summary"] = {
            "warning_count": len(_coerce_warnings(self.raw_result.get("warnings"))),
            "output_keys": sorted(list(self.raw_result.keys()))[:50],
        }
        
        critical_keys = ("demanda_historica", "values", "expected")
        safe_inputs = _prepare_immutable_payload(self.effective_params, preserve_keys=critical_keys)
        safe_outputs = _prepare_immutable_payload(self.raw_result, preserve_keys=critical_keys)
        safe_context = _prepare_immutable_payload(user_context)
        safe_obs_context = _prepare_immutable_payload(obs_context)

        background_tasks.add_task(
            observatory_service.observe_execution,
            context=safe_context,
            inputs=safe_inputs,
            outputs=safe_outputs,
            model_name=self.model_name,
            observatory_context=safe_obs_context,
        )

    def _build_response(self) -> ModelRunResponse:
        response_payload = {
            "modelName": self.model_name,
            "horizon": _extract_horizon(self.model_name, self.raw_result, self.adapted_output),
            "interpretation": _extract_interpretation(self.raw_result),
            "warnings": [_model_dump(w) for w in _coerce_warnings(self.raw_result.get("warnings"))],
            "modelOutput": self.adapted_output,
        }
        try:
            if hasattr(ModelRunResponse, "model_validate"):
                return ModelRunResponse.model_validate(response_payload)
            return ModelRunResponse.parse_obj(response_payload)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"MODEL_RESPONSE_CONTRACT_VIOLATION: {exc}") from exc