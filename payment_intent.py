from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base

class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    plan: Mapped[str] = mapped_column(String(50), nullable=False) # basic, pro, enterprise
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CLP")
    
    provider: Mapped[str] = mapped_column(String(50), default="mercadopago")
    # created | pending | approved | rejected | expired
    status: Mapped[str] = mapped_column(String(20), default="created")
    
    # Referencia externa (Preference ID o Payment ID de MP)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Modo en que se creó (local | sandbox | prod)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)