from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.database.base import Base


class ObservatoryEvent(Base):
    """
    Modelo unificado y genérico para persistencia observacional.

    Se mantiene deliberadamente simple para evitar romper esquemas ya existentes
    y permitir almacenar distintos tipos de eventos del Observatory en el campo
    payload (interaction, risk_snapshot, trend_snapshot, etc.).
    """

    __tablename__ = "observatory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
