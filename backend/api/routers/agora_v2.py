from fastapi import APIRouter, Query, HTTPException, status, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.api.db_deps import get_db
from backend.agora.agora_v2_service import AgoraV2Service
from backend.agora.family_catalog_service import FamilyCatalogService
from backend.agora.compatibility_alias_adapter import CompatibilityAliasAdapter
from backend.agora.schemas.agora_v2_models import (
    AgoraV2PulseResponse, 
    AgoraV2MarketSummary, 
    AgoraV2ProductSummary, 
    AgoraV2FamilySummary,
    AgoraV2ErrorResponse
)

router = APIRouter(prefix="/agora/v2", tags=["agora_v2"])

v2_service = AgoraV2Service()
catalog_service = FamilyCatalogService()
alias_adapter = CompatibilityAliasAdapter()

@router.get("/health")
async def health():
    return {"status": "ok", "module": "AGORA_V2", "architecture": "canonical"}

@router.get("/markets", response_model=List[AgoraV2MarketSummary])
async def get_markets():
    try:
        return catalog_service.list_markets_from_families()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=AgoraV2ErrorResponse(
                error_code="AGORA_V2_INTERNAL_ERROR",
                message="Error interno controlado en ÁGORA V2.",
                suggestion="Revisar logs del backend y contrato de respuesta.",
                details=str(e)
            ).model_dump()
        )

@router.get("/products", response_model=List[AgoraV2ProductSummary])
async def get_products(market_id: str = Query(..., description="ID canónico o safe del mercado")):
    try:
        canonical_market_id = catalog_service.resolve_market_id(market_id)
        products = catalog_service.list_products_by_market(canonical_market_id)
        if not products:
            # Verificar si el mercado existe realmente
            all_markets = catalog_service.list_markets_from_families()
            market_exists = any(m["id"] == canonical_market_id for m in all_markets)
            if not market_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=AgoraV2ErrorResponse(
                        error_code="MARKET_NOT_FOUND",
                        message=f"No se encontró el mercado: {market_id}",
                        received_id=market_id,
                        suggestion="Use GET /agora/v2/markets para obtener mercados válidos."
                    ).model_dump()
                )
        return products
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=AgoraV2ErrorResponse(
                error_code="AGORA_V2_INTERNAL_ERROR",
                message="Error interno controlado en ÁGORA V2.",
                suggestion="Revisar logs del backend y contrato de respuesta.",
                details=str(e)
            ).model_dump()
        )

@router.get("/families", response_model=List[AgoraV2FamilySummary])
async def get_families(
    market_id: str = Query(..., description="ID canónico o safe del mercado"),
    product_id: str = Query(..., description="ID canónico o safe del producto")
):
    try:
        canonical_market_id = catalog_service.resolve_market_id(market_id)
        canonical_product_id = catalog_service.resolve_product_id(canonical_market_id, product_id)
        
        # Validar mercado
        if not catalog_service.list_products_by_market(canonical_market_id):
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AgoraV2ErrorResponse(
                    error_code="MARKET_NOT_FOUND",
                    message=f"Mercado no encontrado: {market_id}",
                    received_id=market_id,
                    suggestion="Use GET /agora/v2/markets"
                ).model_dump()
            )

        families = catalog_service.list_families_by_product(canonical_market_id, canonical_product_id)
        if not families:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AgoraV2ErrorResponse(
                    error_code="PRODUCT_NOT_FOUND",
                    message=f"Producto no encontrado para el mercado indicado: {product_id}",
                    received_id=product_id,
                    suggestion=f"Use GET /agora/v2/products?market_id={market_id}"
                ).model_dump()
            )
        return families
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=AgoraV2ErrorResponse(
                error_code="AGORA_V2_INTERNAL_ERROR",
                message="Error interno controlado en ÁGORA V2.",
                suggestion="Revisar logs del backend y contrato de respuesta.",
                details=str(e)
            ).model_dump()
        )

@router.get("/resolve-legacy")
async def resolve_legacy(
    market: str = Query(...),
    product: str = Query(...),
    subfamily: str = Query(...)
):
    c_market, c_product, c_family = alias_adapter.resolve_legacy_to_canonical(market, product, subfamily)
    return {
        "legacy": {"market": market, "product": product, "subfamily": subfamily},
        "canonical": {"market_id": c_market, "product_id": c_product, "family_id": c_family},
        "safe": {
            "market_id": catalog_service.resolve_market_id(c_market),
            "product_id": catalog_service.resolve_product_id(c_market, c_product),
            "family_id": catalog_service.resolve_family_id(c_market, c_product, c_family)
        }
    }

@router.get("/pulse", response_model=AgoraV2PulseResponse)
async def get_pulse(
    market_id: str = Query(..., description="ID canónico o safe del mercado"),
    product_id: str = Query(..., description="ID canónico o safe del producto"),
    family_id: str = Query(..., description="ID canónico o safe de la familia"),
    horizon: int = Query(..., description="Horizonte de proyección (3, 6, 12)"),
    unit_cost: Optional[float] = Query(None, description="Costo unitario opcional"),
    user_price: Optional[float] = Query(None, description="Precio de usuario opcional"),
    db: Session = Depends(get_db)
):
    if horizon not in [3, 6, 12]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=AgoraV2ErrorResponse(
                error_code="INVALID_HORIZON",
                message="El horizonte de proyección debe ser 3, 6 o 12 meses.",
                received_value=horizon,
                allowed_values=[3, 6, 12]
            ).model_dump()
        )
        
    try:
        canonical_market_id = catalog_service.resolve_market_id(market_id)
        canonical_product_id = catalog_service.resolve_product_id(canonical_market_id, product_id)
        canonical_family_id = catalog_service.resolve_family_id(canonical_market_id, canonical_product_id, family_id)

        if not catalog_service.validate_market_product_family(canonical_market_id, canonical_product_id, canonical_family_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AgoraV2ErrorResponse(
                    error_code="FAMILY_NOT_FOUND",
                    message=f"No se encontró la familia {family_id} bajo el producto {product_id}.",
                    received_id=family_id,
                    suggestion=f"Use GET /agora/v2/families?market_id={market_id}&product_id={product_id}"
                ).model_dump()
            )

        response = await v2_service.get_pulse(
            market_id=canonical_market_id,
            product_id=canonical_product_id,
            family_id=canonical_family_id,
            horizon=horizon,
            unit_cost=unit_cost,
            user_price=user_price,
            db=db
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=AgoraV2ErrorResponse(
                error_code="AGORA_V2_INTERNAL_ERROR",
                message="Error interno controlado en ÁGORA V2.",
                suggestion="Revisar logs del backend y contrato de respuesta.",
                details=str(e)
            ).model_dump()
        )
