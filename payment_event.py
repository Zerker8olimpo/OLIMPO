from datetime import datetime
from sqlalchemy import String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base

class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payment_intent_id: Mapped[int] = mapped_column(ForeignKey("payment_intents.id"), nullable=False)
    
    source: Mapped[str] = mapped_column(String(50)) # local | verify | webhook
    payload: Mapped[dict] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)