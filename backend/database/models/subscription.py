# backend/database/models/subscription.py
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    plan: Mapped[str] = mapped_column(String(20), nullable=False)          # basic | pro | enterprise
    status: Mapped[str] = mapped_column(String(20), nullable=False)        # active | expired | canceled

    provider: Mapped[str] = mapped_column(String(20), default="google", nullable=False)  # google | mercadopago
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # purchaseToken / payment_id

    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="subscription")
