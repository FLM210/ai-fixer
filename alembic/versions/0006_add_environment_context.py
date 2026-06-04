"""add environment_context table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-03 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0006'
down_revision: str | Sequence[str] | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'environment_context',
        sa.Column('id', sa.Integer(), primary_key=True, default=1),
        sa.Column('content', sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_by', sa.String(), nullable=True, server_default=sa.text("'user'")),
        schema='fixer',
    )

    # 插入默认行
    op.execute("""
        INSERT INTO fixer.environment_context (id, content) VALUES (1, '')
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('environment_context', schema='fixer')
