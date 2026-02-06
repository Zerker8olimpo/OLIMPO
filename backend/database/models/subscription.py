# backend/database/models/subscription.py
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from .payment import PaymentProvider


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # TODO [v1.1]: Eliminar device_id cuando se desacople la suscripción del dispositivo.
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    last_payment_intent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_id: Mapped[str] = mapped_column(String(20), nullable=False)          # basic | pro | enterprise
    status: Mapped[str] = mapped_column(String(20), nullable=False)        # pending | active | expired | canceled

    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider), default=PaymentProvider.GOOGLE, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # purchaseToken / payment_id
    google_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscription")
