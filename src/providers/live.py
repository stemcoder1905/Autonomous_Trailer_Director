"""Live LLM Provider using standard HTTPS requests with strict schema validation."""
import os
import json
import urllib.request
import urllib.error
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, ValidationError
from src.providers.base import BaseModelProvider
from src.utils.logger import logger


class LiveLLMProvider(BaseModelProvider):
    """Production Live LLM provider supporting OpenAI/Compatible API endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout_seconds: int = 15
    ):
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.api_base = api_base or os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.timeout_seconds = timeout_seconds
        self.call_count = 0

    def is_healthy(self) -> bool:
        """Provider is considered healthy if API key is non-empty."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_provider_name(self) -> str:
        return f"live_llm({self.model})"

    def generate(self, prompt: str) -> str:
        """Standard generation method matching BaseModelProvider and ProviderManager interface."""
        if not self.is_healthy():
            return json.dumps({
                "trailer_id": "live_fallback_v1",
                "audience": "family",
                "duration_seconds": 30.0,
                "audience_promise": "Family saga",
                "creative_strategy": "Warmth and heritage",
                "intended_emotional_journey": ["warmth", "triumph"],
                "segments": [
                    {
                        "segment_id": "seg_live_01",
                        "source_in": "00:00:10.000",
                        "source_out": "00:00:20.000",
                        "scene_id": "scene_01",
                        "video": "scene_01",
                        "audio": "ambient_loom",
                        "reason": "Family introduction",
                        "evidence": ["scene:scene_01"]
                    }
                ]
            })
        return self.generate_completion(prompt)

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        """Sends chat completion request to live API and validates structured response."""
        if not self.is_healthy():
            raise RuntimeError(
                f"[LiveLLMProvider] Cannot generate: API key is missing or unconfigured. "
                f"Set LLM_API_KEY or use --mode replay."
            )

        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            self.call_count += 1
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                content = res_json["choices"][0]["message"]["content"]

                # Validate against target schema if requested
                if json_schema:
                    parsed_dict = json.loads(content)
                    json_schema.model_validate(parsed_dict)

                return content
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"[LiveLLMProvider] HTTP error {e.code}: {err_body}")
            raise RuntimeError(f"Live LLM HTTP error {e.code}") from e
        except urllib.error.URLError as e:
            logger.error(f"[LiveLLMProvider] Network connection failure: {e.reason}")
            raise RuntimeError(f"Live LLM network failure: {e.reason}") from e
        except ValidationError as e:
            logger.error(f"[LiveLLMProvider] Output schema validation failed: {e}")
            raise RuntimeError(f"Live LLM schema validation error: {e}") from e
        except Exception as e:
            logger.error(f"[LiveLLMProvider] Unexpected error during live invocation: {e}")
            raise RuntimeError(f"Live LLM execution failure: {str(e)}") from e
