import asyncio
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.agora.price_intelligence.source_clients.mercado_libre_client import MercadoLibreClient
from backend.agora.price_intelligence.query_builder import QueryBuilder
from backend.agora.price_intelligence.product_matcher import ProductMatcher
from backend.agora.price_intelligence.price_normalizer import PriceNormalizer
from backend.agora.price_intelligence.outlier_filter import OutlierFilter
from backend.agora.price_intelligence.price_observation_service import PriceObservationService
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.agora.family_catalog_service import FamilyCatalogService

class PriceObserver:
    """
    TAREA 7: Orquestador del Observador de Precios.
    Coordina la búsqueda, matching, filtrado y persistencia de precios.
    """
    
    def __init__(self):
        self.meli_client = MercadoLibreClient()
        self.query_builder = QueryBuilder()
        self.matcher = ProductMatcher()
        self.normalizer = PriceNormalizer()
        self.outlier_filter = OutlierFilter()
        self.obs_service = PriceObservationService()
        self.catalog = FamilyCatalogService()
        self.snapshot_builder = SnapshotBuilder()

    async def observe_family_prices(
        self,
        db: Session,
        market_id: str,
        product_id: str,
        family_id: str,
        source_id: str = "mercado_libre_mlc",
        max_queries: int = 5,
        limit_per_query: int = 50,
        build_snapshot: bool = True
    ) -> Dict[str, Any]:
        """
        Observa precios para una familia específica.
        """
        # 1. Obtener CFG de la familia
        family_cfg = self.catalog.get_family(market_id, product_id, family_id)
        if not family_cfg:
            return {"error": f"Family {family_id} not found in catalog", "success": False}
            
        # 2. Construir queries
        queries = self.query_builder.build_family_queries(market_id, product_id, family_id, family_cfg)
        
        raw_items = []
        source_error = None
        # 3. Consultar fuente (Mercado Libre)
        for query in queries[:max_queries]:
            try:
                items = await self.meli_client.search_items(db, query, limit=limit_per_query)
                raw_items.extend(items)
            except Exception as e:
                source_error = str(e)
            # Pequeño delay para no saturar si hay muchas queries
            await asyncio.sleep(0.1)
            
        if not raw_items:
            return {
                "family_id": family_id,
                "success": True,
                "raw_count": 0,
                "raw_count_api": 0,
                "matched_count": 0,
                "data_status": "no_data",
                "message": "No items found for the given queries",
                "queries_used": queries[:max_queries],
                "source_status": "error" if source_error else "empty",
                "source_error": source_error
            }
            
        # 4. Matching & Normalización
        matched_observations = []
        skipped_count = 0
        
        for item in raw_items:
            # Validar si el item pertenece a la familia
            match_result = self.matcher.match_item_to_family(item, family_cfg)
            
            if match_result["accepted"]:
                # Normalizar precio y unidad
                norm_result = self.normalizer.normalize_item_price_unit(item, family_cfg)
                
                # Combinar datos para el filtro
                obs_data = {
                    **item,
                    **norm_result,
                    "match_score": match_result["score"],
                    "match_reason": match_result["reason"]
                }
                matched_observations.append(obs_data)
            else:
                skipped_count += 1
                
        # 5. Filtrar Outliers
        valid_observations = self.outlier_filter.filter_price_outliers(matched_observations)
        
        # 6. Persistir en DB
        inserted_count = 0
        for obs in valid_observations:
            # Guardar metadata rica
            metadata = {
                "source_item_id": obs.get("source_item_id"),
                "url": obs.get("url"),
                "match_score": obs.get("match_score"),
                "pack_size": obs.get("pack_size"),
                "raw_price": obs.get("price"),
                "condition": obs.get("condition")
            }
            
            saved = self.obs_service.save_price_observation(
                db=db,
                market_id=market_id,
                product_id=product_id,
                family_id=family_id,
                source=obs["source"],
                source_type=obs["source_type"],
                raw_product_name=obs["title"],
                normalized_product_name=obs["normalized_product_name"],
                price=obs["normalized_unit_price"],
                unit=obs["unit"],
                currency=obs["currency"],
                confidence=obs["match_score"],
                metadata=metadata,
                is_sample=False
            )
            if saved:
                inserted_count += 1
                
        # 7. Reconstruir Snapshot si se solicita
        snapshot_built = False
        data_status = "no_data"
        price_median = 0.0
        
        if build_snapshot and inserted_count > 0:
            month_str = datetime.now(timezone.utc).strftime("%Y-%m")
            snap = self.snapshot_builder.build_monthly_snapshot(db, market_id, product_id, family_id, month_str)
            if snap:
                snapshot_built = True
                data_status = snap.data_status
                price_median = snap.price_median
                
        return {
            "market_id": market_id,
            "product_id": product_id,
            "family_id": family_id,
            "source": source_id,
            "queries": queries,
            "raw_count": len(raw_items),
            "raw_count_api": len(raw_items),
            "matched_count": len(matched_observations),
            "inserted": inserted_count,
            "skipped": skipped_count,
            "snapshot_built": snapshot_built,
            "data_status": data_status,
            "price_median": price_median,
            "confidence": statistics.mean([o["match_score"] for o in valid_observations]) if valid_observations else 0.0,
            "source_status": "ok",
            "source_error": None,
            "queries_used": queries[:max_queries]
        }
