from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base

class PaymentStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class SubscriptionStatus(str, Enum):
    INACTIVE = "inactive"
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
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

class PaymentEvent(Base):
    __tablename__ = "payment_events"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    intent_id: Mapped[int] = mapped_column(ForeignKey("payment_intents.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50)) # webhook | polling | local
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(50))
    signature_validated: Mapped[bool] = mapped_column(Boolean, default=False)

class PALAuditLog(Base):
    __tablename__ = "pal_audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    intent_id: Mapped[int] = mapped_column(ForeignKey("payment_intents.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100))
    previous_status: Mapped[str] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)