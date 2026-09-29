"""Base class and interface for model providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel


class BaseModelProvider(ABC):
    """Abstract interface for LLM / Multimodal AI providers."""

    @abstractmethod
    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        """Generate text completion from prompt."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the model provider is available and responding."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name identifier of the provider."""
        pass
