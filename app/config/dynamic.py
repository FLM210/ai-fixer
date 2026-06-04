"""动态配置服务：从数据库加载可运行时修改的配置项，优先级高于环境变量。"""

from __future__ import annotations

import json
import threading
from typing import Any

import structlog
from sqlalchemy import select

logger = structlog.get_logger(__name__)

# 所有可通过前端管理的配置键及其默认值和类型
# 格式: key -> (default_value, value_type, description, is_secret)
MANAGED_CONFIGS: dict[str, tuple[Any, str, str, bool]] = {
    # --- LLM ---
    "llm_provider": ("anthropic", "str", "LLM 提供商（anthropic / openai）", False),
    "llm_base_url": ("", "str", "LLM API 地址", False),
    "llm_api_key": ("", "str", "LLM API 密钥", True),
    "llm_model": ("", "str", "LLM 模型名称", False),
    "llm_timeout_seconds": (60.0, "float", "LLM 请求超时时间（秒）", False),
    "llm_max_turns": (8, "int", "LLM 最大交互轮数", False),

    # --- 飞书 ---
    "lark_app_id": ("", "str", "飞书应用 App ID", False),
    "lark_app_secret": ("", "str", "飞书应用 App Secret", True),
    "alert_bot_ids": ("", "str", "告警机器人 Sender ID（逗号分隔）", False),
    "card_signing_key": ("", "str", "卡片按钮 HMAC 签名密钥", True),

    # --- Embedding ---
    "embedding_base_url": ("", "str", "Embedding API 地址（为空则复用 LLM）", False),
    "embedding_api_key": ("", "str", "Embedding API 密钥（为空则复用 LLM）", True),
    "embedding_model": ("text-embedding-3-small", "str", "Embedding 模型名称", False),
    "embedding_enabled": (False, "bool", "是否启用向量记忆", False),

    # --- 安全围栏 ---
    "fence_auto_namespaces": ("default,staging", "str", "允许自动修复的命名空间（逗号分隔）", False),
    "fence_max_replica_change": (5, "int", "单次修复最大副本数变更", False),
    "fence_max_auto_fixes_per_hour": (10, "int", "每小时最大自动修复次数", False),
    "fence_max_auto_steps_per_incident": (3, "int", "每个 incident 最大自动修复步数", False),
    "fence_cooldown_seconds": (300, "int", "自动修复冷却时间（秒）", False),
    "fence_require_approval_verbs": (
        "delete,drain,cordon",
        "str",
        "需要审批的操作（逗号分隔）",
        False,
    ),

    # --- 监控: PostgreSQL ---
    "pg_monitor_dsn": ("", "str", "PostgreSQL 监控连接串", True),
    "pg_monitor_enabled": (False, "bool", "是否启用 PostgreSQL 监控", False),

    # --- 监控: Redis ---
    "redis_monitor_url": ("", "str", "Redis 监控连接地址", False),
    "redis_monitor_enabled": (False, "bool", "是否启用 Redis 监控", False),

    # --- 监控: AWS ---
    "aws_access_key_id": ("", "str", "AWS Access Key ID", True),
    "aws_secret_access_key": ("", "str", "AWS Secret Access Key", True),
    "aws_region": ("us-east-1", "str", "AWS 区域", False),
    "aws_enabled": (False, "bool", "是否启用 AWS 监控", False),

    # --- 诊断 ---
    "diagnose_confidence_threshold": (0.7, "float", "置信度阈值，低于此值会触发工具排查（0-1）", False),

    # --- 插件 ---
    "disabled_plugins": ("[]", "json", "已禁用的插件列表（JSON 数组）", False),

    # --- 其他 ---
    "log_level": ("INFO", "str", "日志级别（DEBUG / INFO / WARNING / ERROR）", False),
}

# 配置键到 Settings 属性的映射（用于覆盖 Settings 的属性值）
_CONFIG_TO_SETTINGS_ATTR: dict[str, str] = {
    "llm_provider": "llm_provider",
    "llm_base_url": "llm_base_url",
    "llm_api_key": "llm_api_key",
    "llm_model": "llm_model",
    "llm_timeout_seconds": "llm_timeout_seconds",
    "llm_max_turns": "llm_max_turns",
    "lark_app_id": "lark_app_id",
    "lark_app_secret": "lark_app_secret",
    "alert_bot_ids": "alert_bot_ids_raw",
    "card_signing_key": "card_signing_key",
    "embedding_base_url": "embedding_base_url",
    "embedding_api_key": "embedding_api_key",
    "embedding_model": "embedding_model",
    "embedding_enabled": "embedding_enabled",
    "fence_auto_namespaces": "fence_auto_namespaces",
    "fence_max_replica_change": "fence_max_replica_change",
    "fence_max_auto_fixes_per_hour": "fence_max_auto_fixes_per_hour",
    "fence_max_auto_steps_per_incident": "fence_max_auto_steps_per_incident",
    "fence_cooldown_seconds": "fence_cooldown_seconds",
    "fence_require_approval_verbs": "fence_require_approval_verbs",
    "pg_monitor_dsn": "pg_monitor_dsn",
    "pg_monitor_enabled": "pg_monitor_enabled",
    "redis_monitor_url": "redis_monitor_url",
    "redis_monitor_enabled": "redis_monitor_enabled",
    "aws_access_key_id": "aws_access_key_id",
    "aws_secret_access_key": "aws_secret_access_key",
    "aws_region": "aws_region",
    "aws_enabled": "aws_enabled",
    "diagnose_confidence_threshold": "diagnose_confidence_threshold",
    "log_level": "log_level",
}


def _mask_secret(value: Any) -> str:
    """对密钥类值进行脱敏。"""
    s = str(value)
    if len(s) <= 8:
        return "****"
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


def _cast_value(value: str, value_type: str) -> Any:
    """将字符串值转换为对应的 Python 类型。"""
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        return value.lower() in ("true", "1", "yes")
    if value_type == "json":
        return json.loads(value)
    return value


def _serialize_value(value: Any, value_type: str) -> str:
    """将 Python 值序列化为字符串存储。"""
    if value_type == "bool":
        return "true" if value else "false"
    if value_type == "json":
        return json.dumps(value, ensure_ascii=False)
    return str(value)


class DynamicConfig:
    """动态配置管理器：从数据库加载配置，提供内存缓存和热更新。"""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._loaded = False
        self._lock = threading.Lock()

    async def load(self, session: Any) -> None:
        """从数据库加载所有配置到内存缓存。"""
        from app.db.models.system_config import SystemConfig

        stmt = select(SystemConfig)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        with self._lock:
            self._cache.clear()
            for row in rows:
                self._cache[row.key] = _cast_value(row.value, row.value_type)
            self._loaded = True

        logger.info("dynamic_config_loaded", count=len(rows))

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，优先从缓存读取，未找到则返回默认值。"""
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        # 缓存中没有，返回 MANAGED_CONFIGS 中的默认值
        if key in MANAGED_CONFIGS:
            return MANAGED_CONFIGS[key][0]

        return default

    def get_all(self) -> dict[str, Any]:
        """获取所有配置项（合并 DB 缓存和默认值）。"""
        result = {}
        with self._lock:
            for key, (default, value_type, description, is_secret) in MANAGED_CONFIGS.items():
                value = self._cache.get(key, default)
                # 密钥类字段脱敏显示
                display_value = _mask_secret(value) if is_secret and value else value
                result[key] = {
                    "value": display_value,
                    "raw_value": value,
                    "type": value_type,
                    "description": description,
                    "is_secret": is_secret,
                    "source": "database" if key in self._cache else "default",
                }
        return result

    async def update(self, session: Any, configs: dict[str, Any], updated_by: str = "api") -> None:
        """批量更新配置项到数据库并刷新缓存。"""
        from app.db.models.system_config import SystemConfig

        for key, value in configs.items():
            if key not in MANAGED_CONFIGS:
                logger.warning("skip_unknown_config", key=key)
                continue

            _, value_type, description, _is_secret = MANAGED_CONFIGS[key]
            serialized = _serialize_value(value, value_type)

            # Upsert
            stmt = select(SystemConfig).where(SystemConfig.key == key)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = serialized
                existing.value_type = value_type
                existing.updated_by = updated_by
            else:
                session.add(SystemConfig(
                    key=key,
                    value=serialized,
                    value_type=value_type,
                    description=description,
                    updated_by=updated_by,
                ))

            # 更新缓存
            with self._lock:
                self._cache[key] = _cast_value(serialized, value_type)

        await session.flush()
        logger.info("dynamic_config_updated", keys=list(configs.keys()))

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def apply_to_settings(self, settings: Any) -> None:
        """将 DB 配置覆盖到 Settings 对象的对应属性上。

        调用后 settings 的属性值会被 DB 缓存值替换。
        """
        with self._lock:
            for config_key, attr_name in _CONFIG_TO_SETTINGS_ATTR.items():
                if config_key in self._cache:
                    object.__setattr__(settings, attr_name, self._cache[config_key])


# 全局单例
_dynamic_config: DynamicConfig | None = None


def get_dynamic_config() -> DynamicConfig:
    global _dynamic_config
    if _dynamic_config is None:
        _dynamic_config = DynamicConfig()
    return _dynamic_config
