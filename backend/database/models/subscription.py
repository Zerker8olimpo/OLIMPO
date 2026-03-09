from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    Integer,
    Enum,
)
from sqlalchemy.types import TypeDecorator, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from .payment import PaymentProvider


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def __init__(self, *args, **kwargs):
        kwargs["timezone"] = True
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    last_payment_intent_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    plan_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider),
        default=PaymentProvider.GOOGLE,
        nullable=False,
    )

    # 🔴 CRÍTICO PARA IDPOTENCIA DE COMPRAS
    external_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,  # ← NECESARIO PARA EL TEST DE RACE CONDITION
        index=True,
    )

    google_product_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    start_date: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )

    end_date: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
        index=True,
    )

    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="subscriptions",
    )

    payments = relationship(
        "Payment",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )