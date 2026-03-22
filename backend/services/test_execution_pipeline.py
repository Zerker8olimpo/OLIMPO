import pytest
from unittest.mock import MagicMock, patch
from fastapi import BackgroundTasks

from backend.services.execution_pipeline import ModelExecutionPipeline
from backend.api.schemas.model_io import ModelRunResponse
from backend.observatory.services.observatory_service import observatory_service


@pytest.fixture
def valid_epsilon_params():
    return {
        "demanda_historica": [100, 110, 105, 120, 115],
        "horizonte_meses": 3,
        "product_id": "prod_123",
        "market_id": "market_abc"
    }


@pytest.fixture
def mock_user_context():
    return {
        "gmail": "test@example.com",
        "user_id": "u123",
        "device_id": "device_xyz",
        "app_version": "test",
        "platform": "api"
    }


@patch("backend.services.execution_pipeline._call_helios")
@patch("backend.services.execution_pipeline.runtime_resolver")
@patch("backend.services.execution_pipeline.evaluate_shadow")
def test_pipeline_async_observatory_dispatch(
    mock_evaluate_shadow,
    mock_runtime_resolver,
    mock_call_helios,
    valid_epsilon_params,
    mock_user_context
):
    """
    Valida que el ModelExecutionPipeline se ejecuta sin errores, respeta 
    contratos y delega el envío observacional a BackgroundTasks.
    """
    # 1. Preparar valores de retorno de dependencias (Mocks)
    mock_evaluate_shadow.return_value = {
        "os_state": "STABLE",
        "decision_mode": "STANDARD",
        "confidence": {"effective": 0.95}
    }
    
    # El nuevo contrato del resolver devuelve una tupla: (effective_params, applied_patches)
    mock_runtime_resolver.resolve_model_inputs.return_value = (
        {
            **valid_epsilon_params,
            "_runtime_overlay": {"applied": True}
        },
        [{
            "param": "margen_bruto_pct", 
            "rule": "mock_rule",
            "os_state": "STABLE",
            "base": 0.25, 
            "effective": 0.30, 
            "multiplier": 1.2, 
            "source": "w_shock", 
            "applied": True
        }]
    )
    
    mock_call_helios.return_value = {
        "p50": [116, 117, 118],
        "p95": [120, 125, 130],
        "horizon": 3,
        "interpretation": {"summary": "Tendencia al alza observada"},
        "warnings": []
    }

    background_tasks_mock = MagicMock(spec=BackgroundTasks)
    
    # 2. Ejecutar Pipeline
    pipeline = ModelExecutionPipeline("EPSILON", valid_epsilon_params)
    response = pipeline.execute(background_tasks_mock, mock_user_context)

    # 3. Verificaciones de contrato de respuesta hacia el Frontend
    assert isinstance(response, ModelRunResponse)
    assert response.modelName == "EPSILON"
    assert response.horizon == 3
    
    # 4. Verificaciones de Desacoplamiento (Dispatch Asíncrono)
    background_tasks_mock.add_task.assert_called_once()
    args, kwargs = background_tasks_mock.add_task.call_args
    
    # Validar que se encola la función correcta de observatory_service
    assert args[0] == observatory_service.observe_execution
    
    # Validar inmutabilidad superficial en payloads despachados al background
    assert kwargs["model_name"] == "EPSILON"
    assert kwargs["inputs"]["product_id"] == "prod_123"
    assert "p50" in kwargs["outputs"]
    
    # Validar existencia de la huella de orquestación (Runtime Trace)
    assert "observatory_context" in kwargs
    obs_context = kwargs["observatory_context"]
    assert "shadow_status" in obs_context
    assert obs_context["helios_enriched"] is True