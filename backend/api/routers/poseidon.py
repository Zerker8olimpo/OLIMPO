from fastapi import APIRouter
router = APIRouter(prefix="/poseidon", tags=["Poseidon"])

@router.get("/")
def test_poseidon():
    return {"mensaje": "Router de Poseidon operativo"}