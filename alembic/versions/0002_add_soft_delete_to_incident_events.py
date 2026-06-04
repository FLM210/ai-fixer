"""add soft delete to incident_events

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'incident_events',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        schema='fixer',
    )
    op.add_column(
        'incident_events',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        schema='fixer',
    )


def downgrade() -> None:
    op.drop_column('incident_events', 'deleted_at', schema='fixer')
    op.drop_column('incident_events', 'is_deleted', schema='fixer')
