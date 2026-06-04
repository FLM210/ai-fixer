from app.config.settings import Settings
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient
from app.llm.openai_client import OpenAIClient


def build_llm_client(settings: Settings) -> LLMClient:
    cfg = settings.llm
    if cfg.provider == "anthropic":
        return AnthropicClient(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            model=cfg.model,
            timeout_seconds=cfg.timeout_seconds,
        )
    if cfg.provider == "openai":
        return OpenAIClient(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            model=cfg.model,
            timeout_seconds=cfg.timeout_seconds,
        )
    raise ValueError(f"unsupported provider: {cfg.provider}")
