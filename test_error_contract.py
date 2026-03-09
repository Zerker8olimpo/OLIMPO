import os
from pathlib import Path
import sys
from fastapi.testclient import TestClient
from fastapi import HTTPException, Depends, APIRouter

# Configuración de entorno
ROOT_DIR = Path(__file__).resolve().parent
os.environ["JWT_SECRET"] = "test_secret"

from backend.api.main import app

client = TestClient(app)

# --- Router de Prueba para Simular Errores ---
test_router = APIRouter(prefix="/test-errors")

def mock_require_upgrade():
    # Simula lo que hace require_model_access cuando falta plan
    raise HTTPException(
        status_code=403,
        detail={"action": "UPGRADE_PLAN"}
    )

def mock_device_conflict():
    # Simula conflicto de dispositivo
    raise HTTPException(
        status_code=409,
        detail="DEVICE_MISMATCH"
    )

@test_router.get("/force-403")
def force_403(deps=Depends(mock_require_upgrade)):
    return {"ok": True}

@test_router.get("/force-409")
def force_409(deps=Depends(mock_device_conflict)):
    return {"ok": True}

@test_router.get("/protected")
def protected_route():
    return {"ok": True}

# Inyectamos el router de prueba en la app
app.include_router(test_router)


def test_403_upgrade_plan_contract():
    """
    Valida que el error 403 devuelva el JSON plano {"action": "UPGRADE_PLAN"}
    y NO {"detail": {"action": "UPGRADE_PLAN"}}
    """
    print("\n🧪 Probando Contrato 403 Forbidden (UPGRADE_PLAN)...")
    response = client.get("/test-errors/force-403")
    
    assert response.status_code == 403
    data = response.json()
    
    print(f"   Response: {data}")
    
    # Verificación estricta del contrato
    assert "action" in data, "❌ El body debe contener la clave 'action' en la raíz"
    assert data["action"] == "UPGRADE_PLAN"
    assert "detail" not in data, "❌ No debe haber wrapper 'detail' para este error"
    print("✅ Contrato 403 verificado.")

def test_409_conflict():
    """
    Valida el error 409 estándar.
    """
    print("\n🧪 Probando Contrato 409 Conflict...")
    response = client.get("/test-errors/force-409")
    
    assert response.status_code == 409
    data = response.json()
    print(f"   Response: {data}")
    assert data["detail"] == "DEVICE_MISMATCH"
    print("✅ Contrato 409 verificado.")

if __name__ == "__main__":
    print("--- INICIANDO AUDITORÍA DE ERRORES ---")
    try:
        test_403_upgrade_plan_contract()
        test_409_conflict()
        print("\n🎉 TODOS LOS CONTRATOS DE ERROR VALIDADOS.")
    except AssertionError as e:
        raise AssertionError(f"FALLO DE CONTRATO: {e}") from e