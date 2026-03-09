from __future__ import annotations

import enum
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.base import Base


class PaymentProvider(enum.Enum):
    GOOGLE = "google"
    MERCADOPAGO = "mercadopago"
    MANUAL = "manual"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))

    provider = Column(String, nullable=False)
    amount = Column(Integer, default=0)
    currency = Column(String, default="CLP")

    status = Column(String, default="created")
    external_id = Column(String, nullable=True)

    subscription = relationship("Subscription", back_populates="payments")