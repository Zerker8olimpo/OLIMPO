import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.security.jwt import create_access_token


@pytest.fixture(scope="module")
def client():
    """Cliente de Test para la aplicación FastAPI."""
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """Cabeceras de autenticación con un token válido para tests."""
    token = create_access_token(
        sub="contract_guard_tester",
        user_id=999,
        device_id="test_device_guard",
        email="guard_tester@example.com",
        plan="enterprise",
    )
    return {"Authorization": f"Bearer {token}"}


@patch("backend.api.routers.models.get_user_plan")
@patch("backend.services.model_service.HeliosEngine.run_epsilon")
def test_epsilon_guard_handles_aliases_and_nulls(mock_run_epsilon, mock_get_plan, client, auth_headers):
    """
    Prueba que el adapter de Epsilon puede reconstruir el contrato:
    - Usando `p50`/`p95` si `expected`/`upper` faltan.
    - Convirtiendo `None` en listas vacías.
    """
    # Helios devuelve un output con el contrato antiguo y un campo nulo
    mock_run_epsilon.return_value = {
        "p50": [100.0, 110.0],
        "p95": [150.0, 160.0],
        "compra_sugerida": [160.0],
        "shock_index": None  # Campo que debe ser normalizado a []
    }
    
    # Simulamos que el usuario tiene plan enterprise para pasar el check de entitlement
    mock_get_plan.return_value = "enterprise"

    payload = {"modelName": "EPSILON", "modelParams": {"demanda_historica": [1, 2]}}
    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    output = data["modelOutput"]

    # Verifica que los alias se crearon correctamente
    assert output["expected"] == [100.0, 110.0]
    assert output["upper"] == [150.0, 160.0]
    # Verifica que el valor nulo se convirtió en lista vacía
    assert output["shock_index"] == []
    # Verifica que la compra sugerida se extrajo como float
    assert output["recommendedPurchase"] == 160.0


@patch("backend.api.routers.models.get_user_plan")
@patch("backend.services.model_service.HeliosEngine.run_epsilon")
def test_epsilon_guard_fails_on_unfixable_contract(mock_run_epsilon, mock_get_plan, client, auth_headers):
    """
    Prueba que si Helios devuelve un tipo de dato incorrecto que no se puede normalizar,
    el endpoint falla con un error 500 controlado.
    """
    # Helios devuelve un string donde se espera una lista
    mock_run_epsilon.return_value = {
        "p50": "esto-rompera-pydantic"
    }
    mock_get_plan.return_value = "enterprise"

    payload = {"modelName": "EPSILON", "modelParams": {"demanda_historica": [1, 2]}}
    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 500
    data = response.json()
    assert "MODEL_OUTPUT_CONTRACT_VIOLATION" in data["detail"]


@patch("backend.api.routers.models.get_user_plan")
@patch("backend.services.model_service.HeliosEngine.run_sigma")
def test_sigma_guard_handles_null_lists(mock_run_sigma, mock_get_plan, client, auth_headers):
    """
    Prueba que el adapter de Sigma convierte listas nulas en listas vacías.
    """
    mock_run_sigma.return_value = {
        "demandDt": [1, 2, 3],
        "eoqDt": None,  # Esta lista nula debe ser corregida
        "ropDt": [5, 6, 7]
    }
    mock_get_plan.return_value = "enterprise"

    payload = {"modelName": "SIGMA", "modelParams": {"demanda_historica": [1, 2]}}
    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    output = data["modelOutput"]

    assert output["demandDt"] == [1, 2, 3]
    assert output["eoqDt"] == []  # Verificación clave
    assert output["ropDt"] == [5, 6, 7]


@patch("backend.api.routers.models.get_user_plan")
@patch("backend.services.model_service.HeliosEngine.run_poseidon")
def test_poseidon_guard_enforces_nesting(mock_run_poseidon, mock_get_plan, client, auth_headers):
    """
    Prueba que el adapter de Poseidon envuelve una respuesta plana
    dentro de la estructura anidada {"poseidon": {...}} que el cliente espera.
    """
    # Helios devuelve una estructura plana
    mock_run_poseidon.return_value = {
        "poseidonInventario1": [100, 90],
        "poseidonInventario2": [50, 55],
        "poseidonFlujo": [10, 12]
    }

    mock_get_plan.return_value = "enterprise"
    payload = {"modelName": "POSEIDON", "modelParams": {"demanda_historica": [1, 2]}}
    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    output = data["modelOutput"]

    # Verificación clave: el nesting existe
    assert "poseidon" in output
    poseidon_data = output["poseidon"]
    assert poseidon_data["poseidonInventario1"] == [100, 90]


@patch("backend.api.routers.models.get_user_plan")
@patch("backend.services.model_service.HeliosEngine.run_poseidon")
def test_poseidon_guard_handles_existing_nesting(mock_run_poseidon, mock_get_plan, client, auth_headers):
    """
    Prueba que si Helios ya devuelve la estructura anidada, el adapter la usa correctamente.
    """
    # Helios devuelve la estructura correcta
    mock_run_poseidon.return_value = {
        "poseidon": {
            "poseidonInventario1": [100, 90],
            "poseidonInventario2": [50, 55],
            "poseidonFlujo": [10, 12]
        }
    }

    mock_get_plan.return_value = "enterprise"
    payload = {"modelName": "POSEIDON", "modelParams": {"demanda_historica": [1, 2]}}
    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    output = data["modelOutput"]

    assert "poseidon" in output
    poseidon_data = output["poseidon"]
    assert poseidon_data["poseidonInventario1"] == [100, 90]