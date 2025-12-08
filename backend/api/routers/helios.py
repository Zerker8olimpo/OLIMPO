from fastapi import APIRouter
router = APIRouter(prefix="/helios", tags=["HELIOS Digital Twin"])

@router.get("/")
def test_helios():
    return {"mensaje": "Router de HELIOS operativo"}