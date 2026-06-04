"""add system_configs table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-03 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
# PostgreSQL imports removed for compatibility

from alembic import op

revision: str = '0004'
down_revision: str | Sequence[str] | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'system_configs',
        sa.Column('key', sa.String(128), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(16), nullable=False, server_default=sa.text("'str'")),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_by', sa.String(128), nullable=True),
        schema='fixer',
    )

    # 插入默认配置记录
    op.execute("""
        INSERT INTO fixer.system_configs (key, value, value_type, description) VALUES
        -- LLM
        ('llm_provider', 'anthropic', 'str', 'LLM 提供商（anthropic / openai）'),
        ('llm_base_url', '', 'str', 'LLM API 地址'),
        ('llm_api_key', '', 'str', 'LLM API 密钥'),
        ('llm_model', '', 'str', 'LLM 模型名称'),
        ('llm_timeout_seconds', '60.0', 'float', 'LLM 请求超时时间（秒）'),
        ('llm_max_turns', '8', 'int', 'LLM 最大交互轮数'),
        -- 飞书
        ('lark_app_id', '', 'str', '飞书应用 App ID'),
        ('lark_app_secret', '', 'str', '飞书应用 App Secret'),
        ('alert_bot_ids', '', 'str', '告警机器人 Sender ID（逗号分隔）'),
        ('card_signing_key', '', 'str', '卡片按钮 HMAC 签名密钥'),
        -- Embedding
        ('embedding_base_url', '', 'str', 'Embedding API 地址（为空则复用 LLM）'),
        ('embedding_api_key', '', 'str', 'Embedding API 密钥（为空则复用 LLM）'),
        ('embedding_model', 'text-embedding-3-small', 'str', 'Embedding 模型名称'),
        ('embedding_enabled', 'false', 'bool', '是否启用向量记忆'),
        -- 安全围栏
        ('fence_auto_namespaces', 'default,staging', 'str', '允许自动修复的命名空间（逗号分隔）'),
        ('fence_max_replica_change', '5', 'int', '单次修复最大副本数变更'),
        ('fence_max_auto_fixes_per_hour', '10', 'int', '每小时最大自动修复次数'),
        ('fence_max_auto_steps_per_incident', '3', 'int', '每个 incident 最大自动修复步数'),
        ('fence_cooldown_seconds', '300', 'int', '自动修复冷却时间（秒）'),
        ('fence_require_approval_verbs', 'delete,drain,cordon', 'str', '需要审批的操作（逗号分隔）'),
        -- 监控
        ('pg_monitor_dsn', '', 'str', 'PostgreSQL 监控连接串'),
        ('pg_monitor_enabled', 'false', 'bool', '是否启用 PostgreSQL 监控'),
        ('redis_monitor_url', '', 'str', 'Redis 监控连接地址'),
        ('redis_monitor_enabled', 'false', 'bool', '是否启用 Redis 监控'),
        ('aws_access_key_id', '', 'str', 'AWS Access Key ID'),
        ('aws_secret_access_key', '', 'str', 'AWS Secret Access Key'),
        ('aws_region', 'us-east-1', 'str', 'AWS 区域'),
        ('aws_enabled', 'false', 'bool', '是否启用 AWS 监控'),
        -- 其他
        ('log_level', 'INFO', 'str', '日志级别（DEBUG / INFO / WARNING / ERROR）')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('system_configs', schema='fixer')
