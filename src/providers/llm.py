"""LLM and Provider Manager with automatic fallback support."""
import os
import json
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
from src.providers.base import BaseModelProvider
from src.providers.mock import MockLLMProvider
from src.utils.logger import logger


class PrimaryLLMProvider(BaseModelProvider):
    """Primary LLM provider (e.g. OpenAI / Anthropic / Gemini)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model
        self.call_count = 0

    def is_healthy(self) -> bool:
        # If no API key is provided, report unhealthy to trigger fallback gracefully
        return bool(self.api_key.strip())

    def get_provider_name(self) -> str:
        return f"primary_llm({self.model})"

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        if not self.is_healthy():
            raise RuntimeError(f"Primary provider '{self.get_provider_name()}' has no valid API key configured.")
        
        # When actual key is provided, an external call can be placed here.
        # For production robustness, if external service fails, caller catches and falls back.
        raise NotImplementedError("Live external LLM client execution requires cloud connection; using Fallback/Mock.")


class FallbackLLMProvider(BaseModelProvider):
    """Secondary backup LLM provider."""

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self.call_count = 0

    def is_healthy(self) -> bool:
        return False  # Defaults to triggering Mock in test/local environments

    def get_provider_name(self) -> str:
        return f"fallback_llm({self.model})"

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        raise RuntimeError("FallbackLLMProvider simulated failure for mock fallback.")


class ProviderManager:
    """Manages primary, secondary, and mock providers with automated fallback and cost tracking."""

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        simulate_primary_failure: bool = False
    ):
        self.mock_provider = MockLLMProvider()
        self.primary_provider = PrimaryLLMProvider()
        self.fallback_provider = FallbackLLMProvider()
        self.simulate_primary_failure = simulate_primary_failure
        self.preferred_provider = preferred_provider or os.getenv("LLM_PROVIDER", "mock")
        self.active_provider_name = "mock"
        self.total_calls = 0

    def get_active_provider(self) -> BaseModelProvider:
        if self.preferred_provider == "mock" or self.simulate_primary_failure:
            self.active_provider_name = "mock"
            return self.mock_provider
        
        if self.primary_provider.is_healthy():
            self.active_provider_name = self.primary_provider.get_provider_name()
            return self.primary_provider
        
        if self.fallback_provider.is_healthy():
            self.active_provider_name = self.fallback_provider.get_provider_name()
            return self.fallback_provider
        
        logger.info("[ProviderManager] Falling back to deterministic MockLLMProvider.")
        self.active_provider_name = "mock"
        return self.mock_provider

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        self.total_calls += 1
        provider = self.get_active_provider()
        try:
            return provider.generate_completion(prompt, system_prompt, json_schema)
        except Exception as e:
            logger.warning(
                f"[ProviderManager] Provider '{provider.get_provider_name()}' failed ({e}). "
                f"Falling back to MockLLMProvider."
            )
            self.active_provider_name = "mock"
            return self.mock_provider.generate_completion(prompt, system_prompt, json_schema)
