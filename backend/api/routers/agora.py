from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional, Any

from backend.agora.agora_service import AgoraService
from backend.agora.schemas.agora_models import AgoraPulseResponse

router = APIRouter(prefix="/agora", tags=["agora"])

# Instancia del servicio (Podría inyectarse vía Depends si se prefiere un Singleton)
agora_service = AgoraService()

@router.get("/health")
async def health():
    return {"status": "ok", "module": "AGORA"}

@router.get("/markets")
async def get_markets():
    return agora_service.get_markets()

@router.get("/products")
async def get_products(market_id: str = Query(..., description="ID del mercado")):
    return agora_service.get_products(market_id)

@router.get("/subfamilies")
async def get_subfamilies(product_id: str = Query(..., description="ID del producto")):
    return agora_service.get_subfamilies(product_id)

@router.get("/pulse", response_model=AgoraPulseResponse)
async def get_pulse(
    market: str = Query(..., description="ID del mercado"),
    product: str = Query(..., description="ID del producto"),
    subfamily: str = Query(..., description="ID de la subfamilia"),
    horizon: int = Query(..., description="Horizonte de proyección (3, 6, 12)"),
    unit_cost: Optional[float] = Query(None, description="Costo unitario del usuario"),
    user_price: Optional[float] = Query(None, description="Precio de venta actual del usuario")
):
    if horizon not in [3, 6, 12]:
        raise HTTPException(status_code=400, detail="Horizonte inválido. Debe ser 3, 6 o 12 meses.")
    
    try:
        response = await agora_service.get_pulse(
            market=market,
            product=product,
            subfamily=subfamily,
            horizon=horizon,
            unit_cost=unit_cost,
            user_price=user_price
        )
        return response
    except Exception as e:
        # En producción usaríamos un logger real y no devolveríamos el error crudo
        raise HTTPException(status_code=500, detail=f"Error interno en ÁGORA: {str(e)}")
