from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base

class AgoraPriceObservation(Base):
    __tablename__ = "agora_price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(100), index=True)
    product_id: Mapped[str] = mapped_column(String(100), index=True)
    family_id: Mapped[str] = mapped_column(String(100), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(50)) # web, manual, etc.
    raw_product_name: Mapped[str] = mapped_column(String(500))
    normalized_product_name: Mapped[str] = mapped_column(String(500))
    unit: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    is_real: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)

class AgoraFamilyMonthlySnapshot(Base):
    __tablename__ = "agora_family_monthly_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(100), index=True)
    product_id: Mapped[str] = mapped_column(String(100), index=True)
    family_id: Mapped[str] = mapped_column(String(100), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True) # YYYY-MM
    price_min: Mapped[float] = mapped_column(Float)
    price_median: Mapped[float] = mapped_column(Float)
    price_avg: Mapped[float] = mapped_column(Float)
    price_max: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[int] = mapped_column(Integer)
    volatility: Mapped[float] = mapped_column(Float)
    data_status: Mapped[str] = mapped_column(String(50))
    source_context: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
