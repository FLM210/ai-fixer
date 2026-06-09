"""add knowledge base tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-08 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision: str = '0007'
down_revision: str | Sequence[str] | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'knowledge_entries',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(64), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default=text("'[]'")),
        sa.Column('source_type', sa.String(32), nullable=False, server_default=text("'manual'")),
        sa.Column('source_incident_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default=text("'published'")),
        sa.Column('created_by', sa.String(64), nullable=True),
        sa.Column('current_revision', sa.Integer(), nullable=False, server_default=text('1')),
        sa.Column('use_count', sa.Integer(), nullable=False, server_default=text('0')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['source_incident_id'], ['fixer.incidents.id'],
            ondelete='SET NULL', name='fk_knowledge_entries_source_incident',
        ),
        schema='fixer',
    )
    op.create_index('ix_knowledge_entries_source_type', 'knowledge_entries', ['source_type'], schema='fixer')
    op.create_index('ix_knowledge_entries_status_created', 'knowledge_entries', ['status', 'created_at'], schema='fixer')

    op.create_table(
        'knowledge_revisions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('entry_id', sa.Uuid(), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(64), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default=text("'[]'")),
        sa.Column('change_summary', sa.String(512), nullable=True),
        sa.Column('created_by', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['entry_id'], ['fixer.knowledge_entries.id'],
            ondelete='CASCADE', name='fk_knowledge_revisions_entry',
        ),
        schema='fixer',
    )
    op.create_index('ix_knowledge_revisions_entry_id', 'knowledge_revisions', ['entry_id'], schema='fixer')
    op.create_index(
        'ix_knowledge_revisions_entry_rev', 'knowledge_revisions',
        ['entry_id', 'revision_number'], unique=True, schema='fixer',
    )

    op.create_table(
        'knowledge_relations',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_id', sa.Uuid(), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('relation_type', sa.String(32), nullable=False, server_default=text("'related'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(
            ['source_id'], ['fixer.knowledge_entries.id'],
            ondelete='CASCADE', name='fk_knowledge_relations_source',
        ),
        sa.ForeignKeyConstraint(
            ['target_id'], ['fixer.knowledge_entries.id'],
            ondelete='CASCADE', name='fk_knowledge_relations_target',
        ),
        schema='fixer',
    )
    op.create_index('ix_knowledge_relations_source', 'knowledge_relations', ['source_id'], schema='fixer')
    op.create_index('ix_knowledge_relations_target', 'knowledge_relations', ['target_id'], schema='fixer')

    # pgvector is optional - use savepoint to safely skip if unavailable
    conn = op.get_bind()
    try:
        has_vector = conn.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).fetchone()
    except Exception:
        has_vector = None

    if has_vector:
        op.execute(text("SAVEPOINT sp_vector"))
        try:
            op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            op.execute(text("ALTER TABLE fixer.knowledge_entries ADD COLUMN embedding vector(1536)"))
            op.execute(text("""
                CREATE INDEX ix_knowledge_entries_embedding
                ON fixer.knowledge_entries USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
        except Exception:
            op.execute(text("ROLLBACK TO SAVEPOINT sp_vector"))


def downgrade() -> None:
    op.drop_table('knowledge_relations', schema='fixer')
    op.drop_table('knowledge_revisions', schema='fixer')
    op.drop_table('knowledge_entries', schema='fixer')
