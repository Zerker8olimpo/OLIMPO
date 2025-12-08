from fastapi import APIRouter
router = APIRouter(prefix="/user", tags=["Usuarios"])

@router.get("/")
def test_user():
    return {"mensaje": "Router de Usuarios operativo"}