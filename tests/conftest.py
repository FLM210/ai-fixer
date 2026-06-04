import os

import pytest

from app.plugins.registry import global_registry

_DEFAULT_ENV: dict[str, str] = {
    "DATABASE_URL": "postgresql+asyncpg://fixer:fixer@localhost:5432/fixer",
    "LLM_PROVIDER": "anthropic",
    "LLM_BASE_URL": "https://api.anthropic.com",
    "LLM_API_KEY": "sk-test-placeholder",
    "LLM_MODEL": "claude-sonnet-4-6",
    "LOG_LEVEL": "INFO",
}


@pytest.fixture(autouse=True, scope="session")
def _ensure_default_env() -> None:
    """对未设置的关键变量补默认值,避免 Settings() 在测试启动时炸。
    已设置的变量(CI / 本地 .env)保持不变。
    """
    for k, v in _DEFAULT_ENV.items():
        os.environ.setdefault(k, v)


@pytest.fixture(autouse=True)
def _isolate_global_plugin_registry() -> None:
    """每个测试前后清空 global_registry,避免 module-level @register 跨测试污染。"""
    global_registry.clear()
    yield
    global_registry.clear()
