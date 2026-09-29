"""Vision Provider Abstraction and Implementations for Real Multimodal Frame Verification.

Provides:
- BaseVisionProvider: Abstract base class
- LiveVisionProvider: Vendor-agnostic multimodal vision model integration (OpenAI / Gemini / Compatible)
- MockVisionProvider: Deterministic replay & mock verification
- VisionProviderManager: Automatic fallback & provenance manager
"""
import os
import json
import base64
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

from src.models.enums import SourceType
from src.utils.logger import logger


class VisionClaimVerificationResult(BaseModel):
    """Structured result returned by vision verification models."""
    scene_id: str
    frame_path: str
    frame_timestamp: str
    claim: str
    vision_observation: str
    characters_detected: List[str] = Field(default_factory=list)
    actions_detected: List[str] = Field(default_factory=list)
    environment_detected: str = "unspecified"
    confidence: float = 1.0
    supported: bool = True
    contradicted: bool = False
    status: str = "PASS"  # "PASS", "FAIL", "REVIEW"
    source_type: str = SourceType.MOCK_MODEL.value
    verification_method: str = "VISION_MODEL"
    verified: bool = True
    notes: Optional[str] = None


class BaseVisionProvider(ABC):
    """Abstract interface for multimodal vision verification providers."""

    @abstractmethod
    def verify_frame_claim(
        self,
        frame_path: Union[str, Path],
        claim: str,
        scene_id: str,
        timestamp: str = "00:00:00.000",
        expected_characters: Optional[List[str]] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> VisionClaimVerificationResult:
        """Verify whether visual frame evidence supports or contradicts a narrative claim."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Returns True if provider is operational and credentials are valid."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class LiveVisionProvider(BaseVisionProvider):
    """Multimodal vision provider sending encoded frames to live vision APIs (OpenAI/Gemini/Compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout_seconds: int = 20,
        review_confidence_threshold: float = 0.75
    ):
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        custom_key = os.getenv("VISION_API_KEY") or os.getenv("LLM_API_KEY", "")

        self.api_key = api_key or custom_key or openai_key or gemini_key or ""
        
        if api_base:
            self.api_base = api_base
        elif os.getenv("VISION_API_BASE") or os.getenv("LLM_API_BASE"):
            self.api_base = os.getenv("VISION_API_BASE") or os.getenv("LLM_API_BASE")
        elif gemini_key and not openai_key and not custom_key:
            self.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        else:
            self.api_base = "https://api.openai.com/v1"

        if model:
            self.model = model
        elif os.getenv("VISION_MODEL"):
            self.model = os.getenv("VISION_MODEL")
        elif gemini_key and not openai_key and not custom_key:
            self.model = "gemini-1.5-flash"
        else:
            self.model = "gpt-4o"

        self.timeout_seconds = timeout_seconds
        self.review_confidence_threshold = review_confidence_threshold
        self.call_count = 0

    def is_healthy(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_provider_name(self) -> str:
        return f"live_vision({self.model})"

    def verify_frame_claim(
        self,
        frame_path: Union[str, Path],
        claim: str,
        scene_id: str,
        timestamp: str = "00:00:00.000",
        expected_characters: Optional[List[str]] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> VisionClaimVerificationResult:
        if not self.is_healthy():
            raise RuntimeError(
                f"[LiveVisionProvider] Cannot verify frame: API key missing. "
                f"Set VISION_API_KEY or use MockVisionProvider."
            )

        f_path = Path(frame_path)
        if not f_path.exists():
            return VisionClaimVerificationResult(
                scene_id=scene_id,
                frame_path=str(f_path),
                frame_timestamp=timestamp,
                claim=claim,
                vision_observation=f"Frame file does not exist at '{f_path}'",
                confidence=0.0,
                supported=False,
                contradicted=True,
                status="FAIL",
                source_type=source_type.value,
                verification_method="VISION_MODEL",
                verified=False,
                notes="Frame file missing"
            )

        # Base64 encode the frame
        with open(f_path, "rb") as img_f:
            b64_img = base64.b64encode(img_f.read()).decode("utf-8")

        prompt = (
            f"You are a strict multimodal verification agent inspecting video frame '{f_path.name}'.\n"
            f"Scene ID: {scene_id}\n"
            f"Frame Timestamp: {timestamp}\n"
            f"Expected Characters: {expected_characters or []}\n"
            f"Claim to verify: '{claim}'\n\n"
            "Return a JSON object with this exact schema:\n"
            "{\n"
            "  \"observation\": \"detailed visual description of what is seen\",\n"
            "  \"characters_detected\": [\"names or descriptions\"],\n"
            "  \"actions_detected\": [\"actions happening\"],\n"
            "  \"environment\": \"environment description\",\n"
            "  \"supported\": true or false,\n"
            "  \"contradicted\": true or false,\n"
            "  \"confidence\": 0.0 to 1.0\n"
            "}"
        )

        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        self.call_count += 1
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            confidence = float(parsed.get("confidence", 0.9))
            supported = bool(parsed.get("supported", True))
            contradicted = bool(parsed.get("contradicted", False))

            if confidence < self.review_confidence_threshold:
                status = "REVIEW"
            elif contradicted or not supported:
                status = "FAIL"
            else:
                status = "PASS"

            return VisionClaimVerificationResult(
                scene_id=scene_id,
                frame_path=str(f_path),
                frame_timestamp=timestamp,
                claim=claim,
                vision_observation=parsed.get("observation", "Live vision model processed frame."),
                characters_detected=parsed.get("characters_detected", []),
                actions_detected=parsed.get("actions_detected", []),
                environment_detected=parsed.get("environment", "detected"),
                confidence=confidence,
                supported=supported,
                contradicted=contradicted,
                status=status,
                source_type=source_type.value,
                verification_method="VISION_MODEL",
                verified=True,
                notes="Verified by live multimodal vision model"
            )


class MockVisionProvider(BaseVisionProvider):
    """Deterministic mock vision provider for offline testing and replay execution."""

    def __init__(self, default_confidence: float = 0.95):
        self.default_confidence = default_confidence
        self.call_count = 0

    def is_healthy(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "mock_vision"

    def verify_frame_claim(
        self,
        frame_path: Union[str, Path],
        claim: str,
        scene_id: str,
        timestamp: str = "00:00:00.000",
        expected_characters: Optional[List[str]] = None,
        source_type: SourceType = SourceType.REPLAY_FIXTURE
    ) -> VisionClaimVerificationResult:
        self.call_count += 1
        claim_lower = claim.lower()

        # Known contradiction signatures for test cases and ground-truth verification
        has_hug = any(w in claim_lower for w in ["hug", "affection", "embrace"])
        has_hostile = any(w in claim_lower for w in ["confrontation", "buyout", "ultimatum", "arguing", "conflict", "hostile", "crush", "scoffing", "shouting"])
        has_peaceful = any(w in claim_lower for w in ["peaceful", "festival"])
        has_violence = any(w in claim_lower for w in ["violence", "vandalism"])

        if (has_hug and has_hostile) or (has_peaceful and has_violence) or ("contradiction:" in claim_lower and "repaired" not in claim_lower):
            return VisionClaimVerificationResult(
                scene_id=scene_id,
                frame_path=str(frame_path),
                frame_timestamp=timestamp,
                claim=claim,
                vision_observation="Visual frame depicts confrontation and aggressive posture; contradicts affectionate/peaceful claim.",
                characters_detected=["Singhania", "Brijesh"],
                actions_detected=["heated confrontation", "buyout ultimatum"],
                environment_detected="hostile confrontation in workshop",
                confidence=0.96,
                supported=False,
                contradicted=True,
                status="FAIL",
                source_type=source_type.value,
                verification_method="MOCK_VISION",
                verified=False,
                notes="Visual contradiction detected: metadata affection claims disproven by frame evidence."
            )

        # Example 2: Explicit contradiction markers in test scenarios
        contradiction_keywords = ["contradiction", "adversarial", "mismatch", "alien", "spaceship", "explosion"]
        if any(k in claim_lower for k in contradiction_keywords):
            return VisionClaimVerificationResult(
                scene_id=scene_id,
                frame_path=str(frame_path),
                frame_timestamp=timestamp,
                claim=claim,
                vision_observation="Frame visual content directly contradicts scene description claim.",
                characters_detected=[],
                actions_detected=["mismatched action"],
                environment_detected="unknown",
                confidence=0.94,
                supported=False,
                contradicted=True,
                status="FAIL",
                source_type=source_type.value,
                verification_method="MOCK_VISION",
                verified=False,
                notes="Contradiction flagged by visual inspector"
            )

        # Example 3: Low confidence threshold test case
        if "low_confidence" in claim_lower or "ambiguous" in claim_lower:
            return VisionClaimVerificationResult(
                scene_id=scene_id,
                frame_path=str(frame_path),
                frame_timestamp=timestamp,
                claim=claim,
                vision_observation="Frame visual is partially occluded / low lighting prevents definitive verification.",
                characters_detected=[],
                actions_detected=[],
                environment_detected="obscured",
                confidence=0.55,
                supported=True,
                contradicted=False,
                status="REVIEW",
                source_type=source_type.value,
                verification_method="MOCK_VISION",
                verified=False,
                notes="Low confidence (0.55 < 0.75): flagged for human editorial review."
            )

        # Standard supported visual claim
        return VisionClaimVerificationResult(
            scene_id=scene_id,
            frame_path=str(frame_path),
            frame_timestamp=timestamp,
            claim=claim,
            vision_observation=f"Frame visually confirms: {claim}",
            characters_detected=expected_characters or ["Dev"],
            actions_detected=["operating loom", "dialogue exchange"],
            environment_detected="heritage textile workshop",
            confidence=self.default_confidence,
            supported=True,
            contradicted=False,
            status="PASS",
            source_type=source_type.value,
            verification_method="MOCK_VISION",
            verified=False,  # Explicit: mock mode never claims real visual verification
            notes="Replay/mock vision evidence"
        )


class VisionProviderManager:
    """Manages active vision verification provider with automatic fallback and provenance."""

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        simulate_failure: bool = False
    ):
        self.live_provider = LiveVisionProvider()
        self.mock_provider = MockVisionProvider()
        self.simulate_failure = simulate_failure
        self.preferred_provider = preferred_provider or os.getenv("VISION_PROVIDER", "mock")
        self.last_provenance: Dict[str, Any] = {
            "source_type": SourceType.MOCK_MODEL.value,
            "verification_method": "MOCK_VISION",
            "verified": False,
            "fallback_used": False
        }

    def verify_frame(
        self,
        frame_path: Union[str, Path],
        claim: str,
        scene_id: str,
        timestamp: str = "00:00:00.000",
        expected_characters: Optional[List[str]] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> VisionClaimVerificationResult:
        if self.preferred_provider == "live" and not self.simulate_failure and self.live_provider.is_healthy():
            try:
                res = self.live_provider.verify_frame_claim(
                    frame_path=frame_path,
                    claim=claim,
                    scene_id=scene_id,
                    timestamp=timestamp,
                    expected_characters=expected_characters,
                    source_type=source_type
                )
                self.last_provenance = {
                    "source_type": SourceType.LIVE_MODEL.value,
                    "verification_method": "VISION_MODEL",
                    "verified": True,
                    "model": self.live_provider.model,
                    "fallback_used": False
                }
                return res
            except Exception as e:
                logger.warning(
                    f"[VisionProviderManager] Live vision failed ({e}). "
                    f"Transparently falling back to MockVisionProvider."
                )
                res = self.mock_provider.verify_frame_claim(
                    frame_path=frame_path,
                    claim=claim,
                    scene_id=scene_id,
                    timestamp=timestamp,
                    expected_characters=expected_characters,
                    source_type=source_type
                )
                res.notes = f"Live vision failed ({str(e)[:100]}); fallback to mock."
                self.last_provenance = {
                    "source_type": SourceType.MOCK_MODEL.value,
                    "verification_method": "MOCK_VISION",
                    "verified": False,
                    "fallback_used": True,
                    "fallback_reason": str(e)
                }
                return res

        # Default mock / replay provider
        res = self.mock_provider.verify_frame_claim(
            frame_path=frame_path,
            claim=claim,
            scene_id=scene_id,
            timestamp=timestamp,
            expected_characters=expected_characters,
            source_type=source_type
        )
        was_fallback = (self.preferred_provider == "live") or self.simulate_failure
        self.last_provenance = {
            "source_type": SourceType.MOCK_MODEL.value,
            "verification_method": "MOCK_VISION",
            "verified": False,
            "fallback_used": was_fallback,
            "fallback_reason": "Simulated live failure" if self.simulate_failure else ("Live credentials not configured" if was_fallback else None)
        }
        return res
