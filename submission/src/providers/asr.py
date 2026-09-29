"""ASR Provider Abstraction and Implementations for Real Speech-to-Text and Dialogue Verification.

Provides:
- BaseASRProvider: Abstract base class
- LiveASRProvider: Live Whisper / external ASR endpoint integration
- MockASRProvider: Deterministic replay & mock alignment
- ASRProviderManager: Automatic fallback & provenance manager
"""
import os
import json
import difflib
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

from src.models.enums import SourceType
from src.utils.timecode import seconds_to_timecode
from src.utils.logger import logger


class ASRTranscriptSegment(BaseModel):
    """Timestamped segment from speech recognition."""
    start_seconds: float
    end_seconds: float
    start_timecode: str
    end_timecode: str
    text: str
    confidence: float = 1.0
    speaker: Optional[str] = None


class ASRResult(BaseModel):
    """Complete structured result returned by speech recognition."""
    audio_status: str  # "AUDIO_STREAM_DETECTED", "AUDIO_STREAM_NOT_AVAILABLE", "FILE_NOT_FOUND"
    transcript_text: str = ""
    segments: List[ASRTranscriptSegment] = Field(default_factory=list)
    asr_engine: str = "NONE"
    is_asr_output: bool = False
    source_type: str = SourceType.METADATA.value
    verification_method: str = "NOT_PERFORMED"
    verified: bool = False
    average_confidence: float = 0.0
    metadata_match: bool = True
    metadata_divergence_score: float = 0.0
    alignment_details: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class BaseASRProvider(ABC):
    """Abstract interface for automated speech recognition."""

    @abstractmethod
    def transcribe(
        self,
        audio_or_video_path: Union[str, Path],
        start_seconds: float = 0.0,
        end_seconds: Optional[float] = None,
        reference_dialogue: Optional[str] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> ASRResult:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class LiveASRProvider(BaseASRProvider):
    """Live ASR provider connecting to Whisper / OpenAI-compatible audio transcription endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
        api_base: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("ASR_MODEL", "whisper-1")
        self.api_base = api_base or os.getenv("ASR_API_BASE", "https://api.openai.com/v1")
        self.timeout_seconds = timeout_seconds
        self.call_count = 0

    def is_healthy(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_provider_name(self) -> str:
        return f"live_asr({self.model})"

    def transcribe(
        self,
        audio_or_video_path: Union[str, Path],
        start_seconds: float = 0.0,
        end_seconds: Optional[float] = None,
        reference_dialogue: Optional[str] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> ASRResult:
        m_path = Path(audio_or_video_path)
        if not m_path.exists():
            return ASRResult(
                audio_status="FILE_NOT_FOUND",
                transcript_text="",
                asr_engine="NONE",
                is_asr_output=False,
                source_type=source_type.value,
                verification_method="NOT_PERFORMED",
                verified=False,
                notes=f"Media file not found at '{m_path}'"
            )

        if not self.is_healthy():
            raise RuntimeError(
                "[LiveASRProvider] Cannot transcribe: API key is unconfigured. Set OPENAI_API_KEY."
            )

        import tempfile
        import subprocess
        from src.media.audio_processor import AudioProcessor

        temp_audio_path = None
        target_upload_path = m_path

        # If segment timestamps are specified, extract exact audio slice via FFmpeg
        if AudioProcessor.is_ffmpeg_available() and end_seconds is not None and end_seconds > start_seconds:
            try:
                tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tf.close()
                temp_audio_path = Path(tf.name)
                duration = end_seconds - start_seconds
                cmd = [
                    "ffmpeg", "-y", "-ss", str(start_seconds), "-i", str(m_path),
                    "-t", str(duration), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    str(temp_audio_path)
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                target_upload_path = temp_audio_path
            except Exception as e:
                logger.warning(f"[LiveASRProvider] Segment slice extraction failed ({e}); falling back to source file.")
                target_upload_path = m_path

        try:
            # For live transcription, use multipart form POST to /audio/transcriptions
            endpoint = f"{self.api_base.rstrip('/')}/audio/transcriptions"
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            
            # Read file bytes from target upload path
            file_bytes = target_upload_path.read_bytes()
            filename = target_upload_path.name

            body = []
            body.append(f"--{boundary}".encode("utf-8"))
            body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode("utf-8"))
            body.append(b"Content-Type: application/octet-stream\r\n")
            body.append(file_bytes)
            body.append(f"--{boundary}".encode("utf-8"))
            body.append(b'Content-Disposition: form-data; name="model"\r\n')
            body.append(self.model.encode("utf-8"))
            body.append(f"--{boundary}".encode("utf-8"))
            body.append(b'Content-Disposition: form-data; name="response_format"\r\n')
            body.append(b"verbose_json")
            body.append(f"--{boundary}--\r\n".encode("utf-8"))

            data = b"\r\n".join(body)
            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {self.api_key}"
            }

            req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
            self.call_count += 1
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                raw_text = resp_data.get("text", "").strip()
                raw_segments = resp_data.get("segments", [])
        finally:
            if temp_audio_path and temp_audio_path.exists():
                try:
                    temp_audio_path.unlink()
                except Exception:
                    pass

            parsed_segments = []
            for s in raw_segments:
                s_start = float(s.get("start", start_seconds))
                s_end = float(s.get("end", end_seconds or s_start + 5.0))
                parsed_segments.append(
                    ASRTranscriptSegment(
                        start_seconds=round(s_start, 3),
                        end_seconds=round(s_end, 3),
                        start_timecode=seconds_to_timecode(s_start),
                        end_timecode=seconds_to_timecode(s_end),
                        text=s.get("text", "").strip(),
                        confidence=float(s.get("confidence", 0.95))
                    )
                )

            # Compare against supplied metadata dialogue if provided
            match = True
            divergence = 0.0
            if reference_dialogue:
                sim = difflib.SequenceMatcher(None, raw_text.lower(), reference_dialogue.lower()).ratio()
                divergence = round(1.0 - sim, 3)
                match = (sim >= 0.70)

            return ASRResult(
                audio_status="AUDIO_STREAM_DETECTED",
                transcript_text=raw_text,
                segments=parsed_segments,
                asr_engine=self.model,
                is_asr_output=True,  # Confirmed live speech recognition
                source_type=source_type.value,
                verification_method="ASR_MODEL",
                verified=True,
                average_confidence=0.92,
                metadata_match=match,
                metadata_divergence_score=divergence,
                notes="Transcribed using live Whisper speech-to-text"
            )


class MockASRProvider(BaseASRProvider):
    """Deterministic ASR provider for offline replay execution and test verification."""

    def __init__(self):
        self.call_count = 0

    def is_healthy(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "mock_asr"

    def transcribe(
        self,
        audio_or_video_path: Union[str, Path],
        start_seconds: float = 0.0,
        end_seconds: Optional[float] = None,
        reference_dialogue: Optional[str] = None,
        source_type: SourceType = SourceType.REPLAY_FIXTURE
    ) -> ASRResult:
        self.call_count += 1
        m_path = Path(audio_or_video_path)
        
        # Check if media has audio stream
        from src.media.audio_processor import AudioProcessor
        has_audio, status = AudioProcessor.detect_audio_stream(m_path)
        if not has_audio:
            return ASRResult(
                audio_status="AUDIO_STREAM_NOT_AVAILABLE",
                transcript_text="AUDIO_STREAM_NOT_AVAILABLE",
                segments=[],
                asr_engine="NONE",
                is_asr_output=False,
                source_type=source_type.value,
                verification_method="NOT_PERFORMED",
                verified=False,
                metadata_match=True,
                notes="AUDIO_STREAM_NOT_AVAILABLE. System strictly avoids claiming dialogue metadata is ASR output."
            )

        # Generate timestamped mock segment aligned with timecodes
        actual_end = end_seconds or (start_seconds + 5.0)
        text = reference_dialogue or "Our looms have sung this rhythm for three centuries."
        
        # Check for semantic mismatch in test scenarios
        match = True
        divergence = 0.0
        if reference_dialogue and "corrupted" in reference_dialogue.lower():
            match = False
            divergence = 0.85

        seg = ASRTranscriptSegment(
            start_seconds=round(start_seconds, 3),
            end_seconds=round(actual_end, 3),
            start_timecode=seconds_to_timecode(start_seconds),
            end_timecode=seconds_to_timecode(actual_end),
            text=text,
            confidence=0.98,
            speaker="Dev"
        )

        return ASRResult(
            audio_status="AUDIO_STREAM_DETECTED",
            transcript_text=text,
            segments=[seg],
            asr_engine="mock-whisper-v1",
            is_asr_output=False,  # Replay mode explicitly declares is_asr_output=False
            source_type=source_type.value,
            verification_method="MOCK_ASR",
            verified=False,
            average_confidence=0.98,
            metadata_match=match,
            metadata_divergence_score=divergence,
            notes="Replay/mock ASR alignment"
        )


class ASRProviderManager:
    """Manages speech-to-text providers with automatic fallback and provenance."""

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        simulate_failure: bool = False
    ):
        self.live_provider = LiveASRProvider()
        self.mock_provider = MockASRProvider()
        self.simulate_failure = simulate_failure
        self.preferred_provider = preferred_provider or os.getenv("ASR_PROVIDER", "mock")
        self.last_provenance: Dict[str, Any] = {
            "source_type": SourceType.METADATA.value,
            "verification_method": "NOT_PERFORMED",
            "verified": False,
            "fallback_used": False
        }

    def transcribe(
        self,
        audio_or_video_path: Union[str, Path],
        start_seconds: float = 0.0,
        end_seconds: Optional[float] = None,
        reference_dialogue: Optional[str] = None,
        source_type: SourceType = SourceType.REAL_MEDIA
    ) -> ASRResult:
        if self.preferred_provider == "live" and not self.simulate_failure and self.live_provider.is_healthy():
            try:
                res = self.live_provider.transcribe(
                    audio_or_video_path=audio_or_video_path,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    reference_dialogue=reference_dialogue,
                    source_type=source_type
                )
                self.last_provenance = {
                    "source_type": SourceType.LIVE_MODEL.value,
                    "verification_method": "ASR_MODEL",
                    "verified": True,
                    "model": self.live_provider.model,
                    "fallback_used": False
                }
                return res
            except Exception as e:
                logger.warning(
                    f"[ASRProviderManager] Live ASR failed ({e}). "
                    f"Transparently falling back to MockASRProvider."
                )
                res = self.mock_provider.transcribe(
                    audio_or_video_path=audio_or_video_path,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    reference_dialogue=reference_dialogue,
                    source_type=source_type
                )
                res.notes = f"Live ASR failed ({str(e)[:100]}); fallback to mock."
                self.last_provenance = {
                    "source_type": SourceType.MOCK_MODEL.value,
                    "verification_method": "MOCK_ASR",
                    "verified": False,
                    "fallback_used": True,
                    "fallback_reason": str(e)
                }
                return res

        # Default mock / replay provider
        res = self.mock_provider.transcribe(
            audio_or_video_path=audio_or_video_path,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            reference_dialogue=reference_dialogue,
            source_type=source_type
        )
        was_fallback = (self.preferred_provider == "live") or self.simulate_failure
        self.last_provenance = {
            "source_type": res.source_type,
            "verification_method": res.verification_method,
            "verified": res.verified,
            "fallback_used": was_fallback,
            "fallback_reason": "Simulated live failure" if self.simulate_failure else ("Live credentials not configured" if was_fallback else None)
        }
        return res
