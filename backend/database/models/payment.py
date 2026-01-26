# backend/database/models/payment.py
from datetime import datetime
import enum

from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class PaymentProvider(str, enum.Enum):
    GOOGLE = "google"
    MERCADOPAGO = "mercadopago"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)     # google | mercadopago
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CLP", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)       # approved | refunded | failed | pending
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
