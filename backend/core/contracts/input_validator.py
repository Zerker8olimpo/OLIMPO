from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


# =========================================================
# Contracts loading
# =========================================================

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "cfg" / "model_input_contracts.json"
)

if not _CONTRACT_PATH.exists():
    raise RuntimeError(f"Model input contracts not found: {_CONTRACT_PATH}")

with _CONTRACT_PATH.open("r", encoding="utf-8") as f:
    MODEL_INPUT_CONTRACTS = json.load(f)


# =========================================================
# Type helpers
# =========================================================

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_float(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool))


def _validate_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)

    if expected_type == "int":
        return _is_int(value)

    if expected_type == "float":
        return _is_float(value)

    if expected_type == "bool":
        return isinstance(value, bool)

    if expected_type == "object":
        return isinstance(value, dict)

    if expected_type == "list[number]":
        if not isinstance(value, list):
            return False
        return all(_is_float(v) for v in value)

    return True


# =========================================================
# Main validator
# =========================================================

def validate_model_input(model_name: str, params: Dict[str, Any]) -> None:
    model_key = str(model_name).upper().strip()
    schema_key = f"{model_key}_INPUT_SCHEMA"

    if schema_key not in MODEL_INPUT_CONTRACTS:
        raise ValueError(f"Unknown model: {model_name}")

    schema = MODEL_INPUT_CONTRACTS[schema_key]

    required = schema.get("required", [])
    optional = schema.get("optional", [])
    types = schema.get("types", {})

    allowed_fields = set(required + optional)

    missing = [field for field in required if field not in params]
    if missing:
        raise ValueError(
            {
                "error": "MISSING_REQUIRED_FIELDS",
                "missing": missing,
                "model": model_key,
            }
        )

    unknown = [field for field in params if field not in allowed_fields]
    if unknown:
        raise ValueError(
            {
                "error": "UNKNOWN_FIELDS",
                "fields": unknown,
                "model": model_key,
            }
        )

    type_errors = []

    for field, value in params.items():
        expected_type = types.get(field)
        if expected_type is None:
            continue

        if not _validate_type(value, expected_type):
            type_errors.append(
                {
                    "field": field,
                    "expected": expected_type,
                    "received": type(value).__name__,
                }
            )

    if type_errors:
        raise ValueError(
            {
                "error": "INVALID_TYPES",
                "fields": type_errors,
                "model": model_key,
            }
        )