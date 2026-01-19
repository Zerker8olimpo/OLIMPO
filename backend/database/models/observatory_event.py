from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.database.base import Base

class ObservatoryEvent(Base):
    """
    Modelo para el Observatorio Estadístico (Side-Channel).
    Registra eventos de ejecución de modelos sin interferir en la lógica de negocio.
    """
    __tablename__ = "observatory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())