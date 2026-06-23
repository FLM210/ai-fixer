from typing import Any

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def _env(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> None:
    for key in [
        "DATABASE_URL",
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "HTTP_HOST",
        "HTTP_PORT",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(key, raising=False)
    for k, v in kwargs.items():
        monkeypatch.setenv(k, str(v))


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
        LLM_PROVIDER="anthropic",
        LLM_BASE_URL="https://api.anthropic.com",
        LLM_API_KEY="sk-test",
        LLM_MODEL="claude-sonnet-4-6",
    )
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/db"
    assert s.llm.provider == "anthropic"
    assert s.llm.base_url == "https://api.anthropic.com"
    assert s.llm.model == "claude-sonnet-4-6"
    assert s.http_host == "0.0.0.0"
    assert s.http_port == 8080
    assert s.log_level == "INFO"


def test_settings_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
        LLM_PROVIDER="bedrock",
        LLM_BASE_URL="https://x",
        LLM_API_KEY="sk",
        LLM_MODEL="m",
    )
    with pytest.raises(ValueError):
        Settings()


def test_settings_loads_redis_and_lark(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db",
        LLM_PROVIDER="anthropic",
        LLM_BASE_URL="https://api.anthropic.com",
        LLM_API_KEY="sk-test",
        LLM_MODEL="claude-sonnet-4-6",
        REDIS_URL="redis://localhost:6379/0",
        LARK_APP_ID="test_id",
        LARK_APP_SECRET="test_secret",
        CARD_SIGNING_KEY="test_key",
    )
    s = Settings()
    assert s.redis_url == "redis://localhost:6379/0"
    assert s.lark_app_id == "test_id"
    assert s.lark_app_secret == "test_secret"
    assert s.card_signing_key == "test_key"
    assert s.alert_bot_ids == []


def test_settings_missing_db_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        LLM_PROVIDER="anthropic",
        LLM_BASE_URL="https://x",
        LLM_API_KEY="sk",
        LLM_MODEL="m",
    )
    with pytest.raises(ValidationError):
        Settings()
