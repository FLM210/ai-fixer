import pytest

from app.llm import LLMClient
from app.llm.anthropic_client import AnthropicClient
from app.llm.factory import build_llm_client
from app.llm.openai_client import OpenAIClient


@pytest.fixture
def base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/db")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "x")


def test_factory_builds_anthropic(base_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    from app.config import Settings

    settings = Settings()
    client = build_llm_client(settings)
    assert isinstance(client, AnthropicClient)
    assert isinstance(client, LLMClient)
    assert client.provider == "anthropic"
    assert client.model == "x"


def test_factory_builds_openai(base_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from app.config import Settings

    settings = Settings()
    client = build_llm_client(settings)
    assert isinstance(client, OpenAIClient)
    assert client.provider == "openai"


def test_factory_rejects_unknown(monkeypatch: pytest.MonkeyPatch, base_env: None) -> None:
    # provider 在 Settings 层就会被拦截,验证 Settings 校验生效
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings()
