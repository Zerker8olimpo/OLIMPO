"""initial schema

Revision ID: 33c95ecb8bd6
Revises:
Create Date: 2026-03-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from backend.database.models.subscription import UTCDateTime

# revision identifiers, used by Alembic.
revision: str = "33c95ecb8bd6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_uuid", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_devices_device_uuid", "devices", ["device_uuid"], unique=True)
    op.create_index("ix_devices_user_id", "devices", ["user_id"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("last_payment_intent_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("GOOGLE", "MERCADOPAGO", "MANUAL", name="paymentprovider"),
            nullable=False,
        ),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.Column("google_product_id", sa.String(length=255), nullable=True),
        sa.Column("start_date", UTCDateTime(), nullable=True),
        sa.Column("end_date", UTCDateTime(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_subscriptions_device_id",
        "subscriptions",
        ["device_id"],
        unique=False,
    )

    op.create_index(
        "ix_subscriptions_end_date",
        "subscriptions",
        ["end_date"],
        unique=False,
    )

    op.create_index(
        "ix_subscriptions_external_ref",
        "subscriptions",
        ["external_ref"],
        unique=True,
    )

    op.create_index(
        "ix_subscriptions_id",
        "subscriptions",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("company", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=60), nullable=True),
        sa.Column("timezone", sa.String(length=60), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_payments_id", "payments", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_payments_id", table_name="payments")
    op.drop_table("payments")

    op.drop_table("user_profiles")

    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_external_ref", table_name="subscriptions")
    op.drop_index("ix_subscriptions_end_date", table_name="subscriptions")
    op.drop_index("ix_subscriptions_device_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_index("ix_devices_device_uuid", table_name="devices")
    op.drop_table("devices")

    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")