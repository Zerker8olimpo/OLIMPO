"""agora_v2_frontend_ready_schema

Revision ID: 20260519100000
Revises: a8d2e3f4b5c6
Create Date: 2026-05-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20260519100000'
down_revision = 'a8d2e3f4b5c6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # 1. Create agora_metadata if it doesn't exist
    if not inspector.has_table('agora_metadata'):
        op.create_table(
            'agora_metadata',
            sa.Column('key', sa.String(length=255), nullable=False),
            sa.Column('value', sa.String(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('key')
        )

    # 2. Add new columns to agora_price_observations
    if inspector.has_table('agora_price_observations'):
        existing_cols = [c['name'] for c in inspector.get_columns('agora_price_observations')]
        if 'is_real' not in existing_cols:
            op.add_column('agora_price_observations', sa.Column('is_real', sa.Boolean(), nullable=True, server_default='1'))
        if 'metadata_json' not in existing_cols:
            op.add_column('agora_price_observations', sa.Column('metadata_json', sa.JSON(), nullable=True))

    # 3. Add new columns to agora_family_monthly_snapshots
    if inspector.has_table('agora_family_monthly_snapshots'):
        existing_cols = [c['name'] for c in inspector.get_columns('agora_family_monthly_snapshots')]
        if 'price_p25' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('price_p25', sa.Float(), nullable=True))
        if 'price_p75' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('price_p75', sa.Float(), nullable=True))
        if 'dispersion_pct' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('dispersion_pct', sa.Float(), nullable=True))
        if 'confidence_avg' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('confidence_avg', sa.Float(), nullable=True))
        if 'data_quality' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('data_quality', sa.String(length=50), nullable=True))
        if 'source_context' not in existing_cols:
            op.add_column('agora_family_monthly_snapshots', sa.Column('source_context', sa.JSON(), nullable=True))

def downgrade() -> None:
    # Downgrade is conservative and avoids dropping data if possible,
    # but for a complete rollback it would drop the columns/tables.
    # Since we added them conditionally, it's safer to leave them or drop them carefully.
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # It's generally risky to drop columns that might contain production data, 
    # but for standard alembic behavior we would remove them.
    # We will just pass to make it safe, as these are additive columns.
    pass
