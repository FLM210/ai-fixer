from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider: str = "anthropic"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 60.0
    max_turns: int = 16


class PostgresMonitorSettings(BaseModel):
    """监控外部 PostgreSQL 实例的连接配置"""
    model_config = ConfigDict(frozen=True)
    dsn: str = ""  # postgresql://user:pass@host:5432/dbname
    enabled: bool = False


class RedisMonitorSettings(BaseModel):
    """监控外部 Redis 实例的连接配置"""
    model_config = ConfigDict(frozen=True)
    url: str = ""  # redis://host:6379/0
    enabled: bool = False


class AWSMonitorSettings(BaseModel):
    """AWS API 访问配置"""
    model_config = ConfigDict(frozen=True)
    access_key_id: str = ""
    secret_access_key: str = ""
    region: str = "us-east-1"
    enabled: bool = False


class SafetyFences(BaseModel):
    """自动修复的安全围栏配置"""
    model_config = ConfigDict(frozen=True)
    auto_namespaces: list[str] = Field(default_factory=lambda: ["default", "staging"])
    max_replica_change: int = 5
    max_auto_fixes_per_hour: int = 10
    max_auto_steps_per_incident: int = 3
    cooldown_seconds: int = 300
    require_approval_verbs: list[str] = Field(
        default_factory=lambda: ["delete", "drain", "cordon"]
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(..., min_length=1)

    http_host: str = "0.0.0.0"
    http_port: int = 8080

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # 扁平 LLM_* 环境变量,通过 .llm 属性聚合
    # 可从数据库加载，环境变量仅作为 fallback
    llm_provider: str = "anthropic"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 60.0
    llm_max_turns: int = 8

    # Redis（应用自身）
    redis_url: str = "redis://localhost:6379/0"

    # 飞书
    lark_app_id: str = ""
    lark_app_secret: str = ""
    alert_bot_ids_raw: str = ""  # 逗号分隔的 bot ID 列表
    card_signing_key: str = ""

    # Embedding API（用于 incident 向量记忆，默认复用 LLM 配置）
    embedding_base_url: str = ""  # 为空时使用 llm_base_url
    embedding_api_key: str = ""   # 为空时使用 llm_api_key
    embedding_model: str = "text-embedding-3-small"
    embedding_enabled: bool = False

    # 基础设施监控（监控外部实例，非应用自身）
    pg_monitor_dsn: str = ""
    pg_monitor_enabled: bool = False
    redis_monitor_url: str = ""
    redis_monitor_enabled: bool = False
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_enabled: bool = False

    # 安全围栏
    fence_auto_namespaces: str = "default,staging"  # 逗号分隔
    fence_max_replica_change: int = 5
    fence_max_auto_fixes_per_hour: int = 10
    fence_max_auto_steps_per_incident: int = 3
    fence_cooldown_seconds: int = 300
    fence_require_approval_verbs: str = "delete,drain,cordon"  # 逗号分隔

    # 诊断
    diagnose_confidence_threshold: float = 0.7

    @property
    def alert_bot_ids(self) -> list[str]:
        if not self.alert_bot_ids_raw:
            return []
        return [x.strip() for x in self.alert_bot_ids_raw.split(",") if x.strip()]

    @property
    def llm(self) -> LLMSettings:
        return LLMSettings(
            provider=self.llm_provider,
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            model=self.llm_model,
            timeout_seconds=self.llm_timeout_seconds,
            max_turns=self.llm_max_turns,
        )

    @property
    def embedding(self) -> dict[str, str]:
        return {
            "base_url": self.embedding_base_url or self.llm_base_url,
            "api_key": self.embedding_api_key or self.llm_api_key,
            "model": self.embedding_model,
        }

    @property
    def pg_monitor(self) -> PostgresMonitorSettings:
        return PostgresMonitorSettings(dsn=self.pg_monitor_dsn, enabled=self.pg_monitor_enabled)

    @property
    def redis_monitor(self) -> RedisMonitorSettings:
        return RedisMonitorSettings(url=self.redis_monitor_url, enabled=self.redis_monitor_enabled)

    @property
    def aws_monitor(self) -> AWSMonitorSettings:
        return AWSMonitorSettings(
            access_key_id=self.aws_access_key_id,
            secret_access_key=self.aws_secret_access_key,
            region=self.aws_region,
            enabled=self.aws_enabled,
        )

    @property
    def safety_fences(self) -> SafetyFences:
        return SafetyFences(
            auto_namespaces=[ns.strip() for ns in self.fence_auto_namespaces.split(",")],
            max_replica_change=self.fence_max_replica_change,
            max_auto_fixes_per_hour=self.fence_max_auto_fixes_per_hour,
            max_auto_steps_per_incident=self.fence_max_auto_steps_per_incident,
            cooldown_seconds=self.fence_cooldown_seconds,
            require_approval_verbs=[v.strip() for v in self.fence_require_approval_verbs.split(",")],
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
