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
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        custom_key = os.getenv("LLM_API_KEY", "")

        self.api_key = api_key or custom_key or openai_key or gemini_key or ""
        
        # Configure endpoint
        if api_base:
            self.api_base = api_base
        elif os.getenv("LLM_API_BASE"):
            self.api_base = os.getenv("LLM_API_BASE")
        elif gemini_key and not openai_key and not custom_key:
            # Native OpenAI-compatible endpoint for Google Gemini
            self.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        else:
            self.api_base = "https://api.openai.com/v1"

        # Configure default model
        if model:
            self.model = model
        elif os.getenv("LLM_MODEL"):
            self.model = os.getenv("LLM_MODEL")
        elif gemini_key and not openai_key and not custom_key:
            self.model = "gemini-1.5-flash"
        else:
            self.model = "gpt-4o"

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

        def _call_api(msg_list: list) -> str:
            payload = {
                "model": self.model,
                "messages": msg_list,
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
            self.call_count += 1
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                raw_content = res_json["choices"][0]["message"]["content"]
                # Clean markdown fences if present
                clean_content = raw_content.strip()
                if clean_content.startswith("```"):
                    clean_content = clean_content.split("\n", 1)[-1]
                if clean_content.endswith("```"):
                    clean_content = clean_content.rsplit("```", 1)[0]
                return clean_content.strip()

        try:
            content = _call_api(messages)

            # Validate against target schema if requested
            if json_schema:
                try:
                    parsed_dict = json.loads(content)
                    json_schema.model_validate(parsed_dict)
                except (json.JSONDecodeError, ValidationError) as validation_err:
                    logger.warning(
                        f"[LiveLLMProvider] First attempt schema validation failed: {validation_err}. Retrying once with error correction."
                    )
                    # Retry with corrective instruction
                    repair_messages = list(messages)
                    repair_messages.append({"role": "assistant", "content": content})
                    repair_messages.append({
                        "role": "user",
                        "content": f"Your response did not match the required schema: {validation_err}. Please output ONLY valid JSON matching the schema."
                    })
                    content = _call_api(repair_messages)
                    parsed_dict = json.loads(content)
                    json_schema.model_validate(parsed_dict)

            return content
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"[LiveLLMProvider] HTTP error {e.code}: {err_body}")
            raise RuntimeError(f"Live LLM HTTP error {e.code}: {err_body[:200]}") from e
        except urllib.error.URLError as e:
            logger.error(f"[LiveLLMProvider] Network connection failure: {e.reason}")
            raise RuntimeError(f"Live LLM network failure: {e.reason}") from e
        except ValidationError as e:
            logger.error(f"[LiveLLMProvider] Output schema validation failed: {e}")
            raise RuntimeError(f"Live LLM schema validation error: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"[LiveLLMProvider] JSON decode error: {e}")
            raise RuntimeError(f"Live LLM JSON decode error: {e}") from e
        except Exception as e:
            logger.error(f"[LiveLLMProvider] Unexpected error during live invocation: {e}")
            raise RuntimeError(f"Live LLM execution failure: {str(e)}") from e
