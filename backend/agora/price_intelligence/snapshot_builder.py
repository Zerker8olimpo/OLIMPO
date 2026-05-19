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
        
        # We need a minimum sample size to consider it reliable
        if sample_size < 3:
            data_status = "fallback_available"
            data_quality = "low"
        elif sample_size < 10:
            data_status = "real_available"
            data_quality = "medium"
        else:
            data_status = "real_available"
            data_quality = "high"
            
        price_min = min(prices)
        price_max = max(prices)
        price_avg = sum(prices) / sample_size
        price_median = statistics.median(prices)
        
        # Calculate Percentiles
        try:
            # Simple percentile calculation for small datasets
            def get_percentile(data, p):
                size = len(data)
                return sorted(data)[int(round(p * size + 0.5)) - 1]
            
            price_p25 = get_percentile(prices, 0.25)
            price_p75 = get_percentile(prices, 0.75)
        except Exception:
            price_p25 = price_min
            price_p75 = price_max

        # Dispersion: (P75-P25)/Median
        dispersion_pct = (price_p75 - price_p25) / price_median if price_median > 0 else 0
        
        # Confidence avg
        conf_avg = statistics.mean([obs.confidence for obs in observations])
        
        # Basic volatility: (max - min) / avg
        volatility = (price_max - price_min) / price_avg if price_avg > 0 else 0
        
        source_mix = list(set([obs.source for obs in observations]))
        
        # Check if snapshot already exists
        stmt_snap = select(AgoraFamilyMonthlySnapshot).where(
            AgoraFamilyMonthlySnapshot.family_id == s_family_id,
            AgoraFamilyMonthlySnapshot.month == month
        )
        existing = db.execute(stmt_snap).scalars().first()
        
        if existing:
            existing.price_min = price_min
            existing.price_p25 = price_p25
            existing.price_median = price_median
            existing.price_avg = price_avg
            existing.price_p75 = price_p75
            existing.price_max = price_max
            existing.sample_size = sample_size
            existing.volatility = volatility
            existing.dispersion_pct = dispersion_pct
            existing.confidence_avg = conf_avg
            existing.data_status = data_status
            existing.data_quality = data_quality
            existing.source_context = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources_used": source_mix,
                "source_count": len(source_mix)
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
            price_p25=price_p25,
            price_median=price_median,
            price_avg=price_avg,
            price_p75=price_p75,
            price_max=price_max,
            sample_size=sample_size,
            volatility=volatility,
            dispersion_pct=dispersion_pct,
            confidence_avg=conf_avg,
            data_status=data_status,
            data_quality=data_quality,
            source_context={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources_used": source_mix,
                "source_count": len(source_mix)
            }
        )
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
