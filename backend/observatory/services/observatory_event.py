from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from sqlalchemy import String, DateTime, Integer, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base

class ObservatoryEvent(Base):
    """
    Tabla de auditoría y observación estadística.
    Almacena eventos de interacción sin afectar la lógica de negocio.
    """
    __tablename__ = "observatory_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    
    user_id_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_key: Mapped[str] = mapped_column(String(100), nullable=False)
    market_key: Mapped[str] = mapped_column(String(100), nullable=False)
    
    app_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_quality: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    risk_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    helios_gap: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    server_node: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    errors: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)


class TrendSnapshotEntry(Base):
    """
    Persistencia de snapshots de tendencia.
    """
    __tablename__ = "observatory_trend_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    trend_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    trend_strength: Mapped[float] = mapped_column(Float, nullable=False)
    slope: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    
    observation_window: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)