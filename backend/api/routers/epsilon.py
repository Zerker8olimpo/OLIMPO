from fastapi import APIRouter

router = APIRouter(prefix="/epsilon", tags=["Epsilon"])

@router.get("/")
def test_epsilon():
    return {"mensaje": "Router de Epsilon operativo"}