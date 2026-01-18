import uuid
from sqlalchemy import Column, String, DateTime, JSON, Enum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.database.base import Base
from backend.database.models.payment import PaymentProvider

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(PaymentProvider), nullable=False)
    event_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload = Column(JSON, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),)