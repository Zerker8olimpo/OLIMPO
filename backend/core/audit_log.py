from datetime import datetime
from sqlalchemy import String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base

class PALAuditLog(Base):
    __tablename__ = "pal_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    intent_id: Mapped[int] = mapped_column(ForeignKey("payment_intents.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100)) # e.g. "TRANSITION_APPROVED"
    previous_status: Mapped[str] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)