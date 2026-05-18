"""add agora history tables

Revision ID: a8d2e3f4b5c6
Revises: 33c95ecb8bd6
Create Date: 2026-05-18

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a8d2e3f4b5c6"
down_revision: Union[str, Sequence[str], None] = "33c95ecb8bd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. agora_price_observations
    op.create_table(
        "agora_price_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_id", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("family_id", sa.String(length=100), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("raw_product_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_product_name", sa.String(length=500), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_real", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agora_price_observations_market_id", "agora_price_observations", ["market_id"], unique=False)
    op.create_index("ix_agora_price_observations_product_id", "agora_price_observations", ["product_id"], unique=False)
    op.create_index("ix_agora_price_observations_family_id", "agora_price_observations", ["family_id"], unique=False)
    op.create_index("ix_agora_price_observations_observed_at", "agora_price_observations", ["observed_at"], unique=False)

    # 2. agora_family_monthly_snapshots
    op.create_table(
        "agora_family_monthly_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_id", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("family_id", sa.String(length=100), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("price_min", sa.Float(), nullable=False),
        sa.Column("price_median", sa.Float(), nullable=False),
        sa.Column("price_avg", sa.Float(), nullable=False),
        sa.Column("price_max", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("data_status", sa.String(length=50), nullable=False),
        sa.Column("source_context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agora_family_monthly_snapshots_market_id", "agora_family_monthly_snapshots", ["market_id"], unique=False)
    op.create_index("ix_agora_family_monthly_snapshots_product_id", "agora_family_monthly_snapshots", ["product_id"], unique=False)
    op.create_index("ix_agora_family_monthly_snapshots_family_id", "agora_family_monthly_snapshots", ["family_id"], unique=False)
    op.create_index("ix_agora_family_monthly_snapshots_month", "agora_family_monthly_snapshots", ["month"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("agora_family_monthly_snapshots")
    op.drop_table("agora_price_observations")
