import os
from pathlib import Path
import sys

# =========================================================
# Project root detection
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# =========================================================
# Environment mocks
# =========================================================

os.environ["GOOGLE_PLAY_PUBLIC_KEY"] = "mock_key_for_contract_validation"
os.environ["JWT_SECRET"] = "test_secret_olimpo"

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")


# =========================================================
# Imports
# =========================================================

import pytest
from fastapi.testclient import TestClient

try:
    from backend.api.main import app
    from backend.api.security.jwt import create_access_token
except ImportError as e:
    raise RuntimeError(f"Error importando la aplicación OLIMPO: {e}") from e


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():

    # La firma de create_access_token cambió. Ahora requiere argumentos de palabra clave.
    # Se eliminó el argumento 'data'.
    token = create_access_token(
        sub="contract_tester",
        user_id=1,
        device_id="test_device_enterprise",
        email="contract_tester@example.com",  # Argumento requerido añadido
        plan="enterprise",  # Argumento requerido añadido
    )

    return {"Authorization": f"Bearer {token}"}


# =========================================================
# Bootstrap Contract
# =========================================================

def test_bootstrap_contract(client, auth_headers):

    response = client.get("/bootstrap", headers=auth_headers)

    assert response.status_code == 200, f"Fallo en Bootstrap: {response.text}"

    data = response.json()

    assert "user" in data
    assert "subscription" in data

    sub = data["subscription"]

    assert "models_enabled" in sub
    assert isinstance(sub["models_enabled"], list)


# =========================================================
# EPSILON contract
# =========================================================

def test_epsilon_run_contract(client, auth_headers):

    payload = {
        "modelName": "EPSILON",
        "modelParams": {
            "demanda_historica": [120,130,140,150,160,170],
            "product_id": "SKU_TEST",
            "market_id": "CL",
            "horizonte_meses": 3
        }
    }

    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200, f"Epsilon error: {response.text}"

    body = response.json()

    assert "modelName" in body
    assert "modelOutput" in body
    assert "warnings" in body
    assert "interpretation" in body

    assert body["modelName"] == "EPSILON"

    # Verificación de contrato de salida
    output = body["modelOutput"]
    assert "expected" in output and isinstance(output["expected"], list)
    assert "upper" in output and isinstance(output["upper"], list)
    assert "lower" in output and isinstance(output["lower"], list)
    assert "recommendedPurchase" in output and isinstance(output["recommendedPurchase"], float)
    assert len(output["expected"]) == len(output["upper"])


# =========================================================
# SIGMA contract
# =========================================================

def test_sigma_run_contract(client, auth_headers):

    payload = {
        "modelName": "SIGMA",
        "modelParams": {
            "demanda_historica": [120,130,140,150,160,170],
            "product_id": "SKU_TEST",
            "market_id": "CL",
            "costo_unitario": 10,
            "costo_pedido": 100,
            "costo_mantencion_pct": 0.25
        }
    }

    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200, f"Sigma error: {response.text}"

    body = response.json()

    assert body["modelName"] == "SIGMA"

    # Verificación de contrato de salida
    output = body["modelOutput"]
    assert "demandDt" in output and isinstance(output["demandDt"], list)
    assert "eoqDt" in output and isinstance(output["eoqDt"], list)
    assert "ropDt" in output and isinstance(output["ropDt"], list)


# =========================================================
# POSEIDON contract
# =========================================================

def test_poseidon_run_contract(client, auth_headers):

    payload = {
        "modelName": "POSEIDON",
        "modelParams": {
            "demanda_historica": [100,110,120,130],
            "inventario_inicial_tanque1": 1000,
            "inventario_inicial_tanque2": 500
        }
    }

    response = client.post("/models/run", json=payload, headers=auth_headers)

    assert response.status_code == 200, f"Poseidon error: {response.text}"

    body = response.json()

    assert body["modelName"] == "POSEIDON"

    # Verificación de contrato de salida (nesting)
    output = body["modelOutput"]
    assert "poseidon" in output
    poseidon = output["poseidon"]
    assert "poseidonInventario1" in poseidon and isinstance(poseidon["poseidonInventario1"], list)
    assert "poseidonInventario2" in poseidon and isinstance(poseidon["poseidonInventario2"], list)
    assert "poseidonFlujo" in poseidon and isinstance(poseidon["poseidonFlujo"], list)


# =========================================================
# Runner
# =========================================================

if __name__ == "__main__":

    print("🚀 Iniciando Auditoría de Contratos - OLIMPO Backend")

    pytest.main(["-v", __file__])