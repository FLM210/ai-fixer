"""add llm_turns table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
# PostgreSQL imports removed for compatibility

from alembic import op

revision: str = '0005'
down_revision: str | Sequence[str] | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'llm_turns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('fixer.incidents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('phase', sa.String(32), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column('tool_name', sa.String(128), nullable=True),
        sa.Column('tool_input', sa.JSON(), nullable=True),
        sa.Column('tool_output', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        schema='fixer',
    )


def downgrade() -> None:
    op.drop_table('llm_turns', schema='fixer')
