"""add learning models and incident extensions

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
# PostgreSQL imports removed for compatibility

from alembic import op

revision: str = '0003'
down_revision: str | Sequence[str] | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Incident 扩展字段
    op.add_column(
        'incidents',
        sa.Column('resolution_type', sa.String(32), nullable=True),
        schema='fixer',
    )
    op.add_column(
        'incidents',
        sa.Column('resolution_time_seconds', sa.Integer(), nullable=True),
        schema='fixer',
    )
    op.add_column(
        'incidents',
        sa.Column('llm_cost_tokens', sa.Integer(), nullable=True, server_default=sa.text('0')),
        schema='fixer',
    )

    # RepairOutcome 表
    op.create_table(
        'repair_outcomes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('fixer.incidents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('execution_id', sa.String(36), sa.ForeignKey('fixer.fix_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plugin_name', sa.String(128), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('metrics_before', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('metrics_after', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema='fixer',
    )

    # DiagnosticPath 表
    op.create_table(
        'diagnostic_paths',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('fixer.incidents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('plugin_name', sa.String(128), nullable=False),
        sa.Column('args', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('output_summary', sa.String(2048), nullable=True),
        sa.Column('evidence_produced', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema='fixer',
    )


def downgrade() -> None:
    op.drop_table('diagnostic_paths', schema='fixer')
    op.drop_table('repair_outcomes', schema='fixer')
    op.drop_column('incidents', 'llm_cost_tokens', schema='fixer')
    op.drop_column('incidents', 'resolution_time_seconds', schema='fixer')
    op.drop_column('incidents', 'resolution_type', schema='fixer')
