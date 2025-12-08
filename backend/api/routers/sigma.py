from fastapi import APIRouter
router = APIRouter(prefix="/sigma", tags=["Sigma"])

@router.get("/")
def test_sigma():
    return {"mensaje": "Router de Sigma operativo"}