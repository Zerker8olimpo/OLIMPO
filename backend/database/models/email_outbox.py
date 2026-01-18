import uuid
import enum
from sqlalchemy import Column, String, DateTime, JSON, Integer, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.database.base import Base

class EmailStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

class EmailType(str, enum.Enum):
    SUBSCRIPTION_CONFIRMED = "SUBSCRIPTION_CONFIRMED"
    EXPIRY_WARNING = "EXPIRY_WARNING"
    PAYMENT_FAILED = "PAYMENT_FAILED"

class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    email_to = Column(String, nullable=False)
    email_type = Column(Enum(EmailType), nullable=False)
    subject = Column(String, nullable=False)
    template_data = Column(JSON, nullable=False, default=dict)
    status = Column(Enum(EmailStatus), nullable=False, default=EmailStatus.PENDING)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)