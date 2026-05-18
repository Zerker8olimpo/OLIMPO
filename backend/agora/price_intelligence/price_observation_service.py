from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
import json

from backend.database.models.agora import AgoraPriceObservation
from backend.agora.id_normalization_service import IdNormalizationService

class PriceObservationService:
    def save_price_observation(
        self,
        db: Session,
        market_id: str,
        product_id: str,
        family_id: str,
        source: str,
        source_type: str,
        raw_product_name: str,
        normalized_product_name: str,
        price: float,
        unit: str = "unidad",
        currency: str = "CLP",
        confidence: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
        is_sample: bool = False
    ) -> Optional[AgoraPriceObservation]:
        
        # Validar precio
        if price <= 0:
            return None
            
        # Normalizar IDs
        s_market_id = IdNormalizationService.build_safe_id(market_id)
        s_product_id = IdNormalizationService.build_safe_id(product_id)
        s_family_id = IdNormalizationService.build_safe_id(family_id)
        
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Evitar duplicados exactos en el mismo día
        stmt = select(AgoraPriceObservation).where(
            AgoraPriceObservation.family_id == s_family_id,
            AgoraPriceObservation.source == source,
            AgoraPriceObservation.raw_product_name == raw_product_name,
            AgoraPriceObservation.price == price,
            AgoraPriceObservation.observed_at >= start_of_day
        )
        
        existing = db.execute(stmt).scalars().first()
        if existing:
            return existing
            
        obs = AgoraPriceObservation(
            market_id=s_market_id,
            product_id=s_product_id,
            family_id=s_family_id,
            observed_at=now,
            source=source,
            source_type=source_type,
            raw_product_name=raw_product_name,
            normalized_product_name=normalized_product_name,
            unit=unit,
            price=price,
            currency=currency,
            confidence=confidence,
            is_real=not is_sample,
            metadata_json=metadata or {}
        )
        
        db.add(obs)
        db.commit()
        db.refresh(obs)
        return obs
