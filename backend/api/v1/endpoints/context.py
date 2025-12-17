from fastapi import APIRouter
from api.schemas.simulation import ContextSchemaResponse

router = APIRouter()

@router.get("/context/schema", response_model=ContextSchemaResponse)
def schema():
    return ContextSchemaResponse(
        required_fields=["producto", "mercado", "demanda_actual", "lead_time", "stock_actual"],
        optional_fields=["variabilidad", "riesgo_aceptado"],
    )