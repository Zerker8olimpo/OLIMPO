from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base
import enum

class PaymentStatus(str, enum.Enum):
    CREATED = "created"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CLP")
    provider: Mapped[str] = mapped_column(String(50), nullable=False) # mercadopago | google | local
    mode: Mapped[str] = mapped_column(String(20), nullable=False)     # local | sandbox | prod
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(String(20), default=PaymentStatus.CREATED)
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)