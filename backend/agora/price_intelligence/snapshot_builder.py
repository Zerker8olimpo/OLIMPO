from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
import statistics

from backend.database.models.agora import AgoraPriceObservation, AgoraFamilyMonthlySnapshot
from backend.agora.id_normalization_service import IdNormalizationService

class SnapshotBuilder:
    def build_monthly_snapshot(
        self,
        db: Session,
        market_id: str,
        product_id: str,
        family_id: str,
        month: str # YYYY-MM
    ) -> Optional[AgoraFamilyMonthlySnapshot]:
        
        s_market_id = IdNormalizationService.build_safe_id(market_id)
        s_product_id = IdNormalizationService.build_safe_id(product_id)
        s_family_id = IdNormalizationService.build_safe_id(family_id)
        
        # Parse month to get start and end dates
        try:
            year_str, month_str = month.split('-')
            y = int(year_str)
            m = int(month_str)
            start_date = datetime(y, m, 1, tzinfo=timezone.utc)
            if m == 12:
                end_date = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end_date = datetime(y, m + 1, 1, tzinfo=timezone.utc)
        except Exception:
            return None

        # Fetch observations
        stmt = select(AgoraPriceObservation).where(
            AgoraPriceObservation.family_id == s_family_id,
            AgoraPriceObservation.observed_at >= start_date,
            AgoraPriceObservation.observed_at < end_date,
            AgoraPriceObservation.price > 0,
            AgoraPriceObservation.is_real == True
        )
        
        observations = db.execute(stmt).scalars().all()
        
        if not observations:
            return None
            
        prices = [obs.price for obs in observations]
        prices.sort()
        
        sample_size = len(prices)
        
        # We need a minimum sample size to consider it reliable, let's say 3 for now
        if sample_size < 3:
            data_status = "fallback_available" # Too few samples, treated as fallback
        else:
            data_status = "real_available"
            
        price_min = min(prices)
        price_max = max(prices)
        price_avg = sum(prices) / sample_size
        price_median = statistics.median(prices)
        
        # Basic volatility: (max - min) / avg
        volatility = (price_max - price_min) / price_avg if price_avg > 0 else 0
        
        # Check if snapshot already exists
        stmt_snap = select(AgoraFamilyMonthlySnapshot).where(
            AgoraFamilyMonthlySnapshot.family_id == s_family_id,
            AgoraFamilyMonthlySnapshot.month == month
        )
        existing = db.execute(stmt_snap).scalars().first()
        
        if existing:
            existing.price_min = price_min
            existing.price_median = price_median
            existing.price_avg = price_avg
            existing.price_max = price_max
            existing.sample_size = sample_size
            existing.volatility = volatility
            existing.data_status = data_status
            existing.source_context = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources_used": list(set([obs.source for obs in observations]))
            }
            db.commit()
            db.refresh(existing)
            return existing
            
        snapshot = AgoraFamilyMonthlySnapshot(
            market_id=s_market_id,
            product_id=s_product_id,
            family_id=s_family_id,
            month=month,
            price_min=price_min,
            price_median=price_median,
            price_avg=price_avg,
            price_max=price_max,
            sample_size=sample_size,
            volatility=volatility,
            data_status=data_status,
            source_context={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources_used": list(set([obs.source for obs in observations]))
            }
        )
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
