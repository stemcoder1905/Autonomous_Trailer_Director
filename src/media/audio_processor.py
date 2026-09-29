"""Audio extraction, speech recognition (ASR), and dialogue alignment verification."""
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Union, Tuple
from src.utils.logger import logger


from src.models.enums import SourceType


class AudioProcessor:
    """Manages audio stem extraction and dialogue transcript verification."""

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Checks if ffmpeg binary exists on PATH."""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def is_whisper_available() -> bool:
        """Checks if whisper or faster_whisper library is importable."""
        try:
            import whisper  # noqa: F401
            return True
        except ImportError:
            try:
                import faster_whisper  # noqa: F401
                return True
            except ImportError:
                return False

    @classmethod
    def get_source_type(cls, media_path: Union[str, Path]) -> SourceType:
        """Identifies if media is replay fixture or external real media."""
        m_str = str(media_path).replace("\\", "/").lower()
        if "sample_data/media/episode_01.mp4" in m_str or "sample_data" in m_str or "synthetic" in m_str:
            return SourceType.REPLAY_FIXTURE
        return SourceType.REAL_MEDIA

    @classmethod
    def detect_audio_stream(cls, media_path: Union[str, Path]) -> Tuple[bool, str]:
        """Detects whether an actual audio stream exists in the media file."""
        m_path = Path(media_path)
        if not m_path.exists():
            return False, "FILE_NOT_FOUND"

        # 1. Probe using FFmpeg if present
        if cls.is_ffmpeg_available():
            try:
                cmd = ["ffmpeg", "-i", str(m_path)]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output = (res.stderr or "") + (res.stdout or "")
                if "Audio:" in output:
                    return True, "AUDIO_STREAM_DETECTED"
                else:
                    return False, "AUDIO_STREAM_NOT_AVAILABLE"
            except Exception:
                pass

        # 2. Pure Python container format probe
        suffix = m_path.suffix.lower()
        if suffix in [".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg"]:
            return True, "AUDIO_STREAM_DETECTED"

        # MP4/MOV atom probe: check for 'soun' handler box
        if suffix in [".mp4", ".mov", ".m4v"]:
            try:
                with open(m_path, "rb") as f:
                    chunk = f.read(1024 * 1024 * 2)  # Read first 2MB
                    if b"soun" in chunk:
                        return True, "AUDIO_STREAM_DETECTED"
            except Exception:
                pass

        return False, "AUDIO_STREAM_NOT_AVAILABLE"

    @classmethod
    def extract_audio(
        cls,
        video_path: Union[str, Path],
        output_wav_path: Union[str, Path]
    ) -> Tuple[bool, str]:
        """Extracts mono 16kHz WAV audio track only when an audio stream actually exists."""
        v_path = Path(video_path)
        out_wav = Path(output_wav_path)

        if not v_path.exists():
            return False, f"Source video file '{v_path}' not found."

        # Detect audio stream first: do not extract audio if none exists
        has_audio, status = cls.detect_audio_stream(v_path)
        if not has_audio:
            return False, "AUDIO_STREAM_NOT_AVAILABLE"

        if not cls.is_ffmpeg_available():
            return False, "FFmpeg binary is not available on PATH; audio extraction running in capability-reported mode."

        out_wav.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-i", str(v_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(out_wav)
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return True, f"Audio successfully extracted to '{out_wav}'"
        except Exception as e:
            return False, f"FFmpeg execution failed: {str(e)}"

    @classmethod
    def transcribe_segment(
        cls,
        video_or_audio_path: Union[str, Path],
        start_seconds: float,
        end_seconds: float,
        reference_dialogue: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribes audio only when an audio stream exists. Never claims metadata dialogue is ASR output."""
        media_path = Path(video_or_audio_path)
        source_type = cls.get_source_type(media_path)
        has_audio, audio_status = cls.detect_audio_stream(media_path)

        # If no audio stream exists, return AUDIO_STREAM_NOT_AVAILABLE
        if not has_audio:
            return {
                "source": str(media_path),
                "source_type": source_type.value,
                "verification_method": "audio_stream_probe",
                "verified": False,
                "audio_verified": False,
                "audio_status": "AUDIO_STREAM_NOT_AVAILABLE",
                "asr_engine": "NONE",
                "is_asr_output": False,
                "transcript": None,
                "dialogue_match": False,
                "similarity": 0.0,
                "note": "AUDIO_STREAM_NOT_AVAILABLE. System strictly avoids claiming dialogue metadata is ASR output."
            }

        has_whisper = cls.is_whisper_available()
        has_ffmpeg = cls.is_ffmpeg_available()

        # If live whisper and ffmpeg are available, perform live ASR
        if has_whisper and media_path.exists() and has_ffmpeg:
            try:
                import whisper
                model = whisper.load_model("tiny")
                res = model.transcribe(str(media_path))
                text = res.get("text", "").strip()
                match_ok, sim = cls.verify_dialogue_match(reference_dialogue or "", text)
                return {
                    "source": str(media_path),
                    "source_type": SourceType.REAL_MEDIA.value,
                    "verification_method": "whisper_asr_transcription",
                    "verified": True,
                    "audio_verified": True,
                    "audio_status": "AUDIO_STREAM_DETECTED",
                    "asr_engine": "whisper_tiny",
                    "is_asr_output": True,
                    "transcript": {
                        "start": start_seconds,
                        "end": end_seconds,
                        "text": text
                    },
                    "dialogue_match": match_ok,
                    "similarity": round(sim, 3)
                }
            except Exception as e:
                logger.warning(f"[AudioProcessor] Whisper transcription error ({e}); reporting capability status.")

        # Audio stream exists but ASR engine is not installed
        return {
            "source": str(media_path),
            "source_type": source_type.value,
            "verification_method": "audio_stream_probe",
            "verified": True,
            "audio_verified": True,
            "audio_status": "AUDIO_STREAM_DETECTED",
            "asr_engine": "WHISPER_NOT_INSTALLED",
            "is_asr_output": False,
            "transcript": None,
            "dialogue_match": False,
            "similarity": 0.0,
            "note": "Audio stream detected. Whisper library not installed; ASR transcription not performed."
        }

    @classmethod
    def get_capability_status(cls) -> Dict[str, Any]:
        """Returns environment audio capability report."""
        ffmpeg_ok = cls.is_ffmpeg_available()
        whisper_ok = cls.is_whisper_available()
        return {
            "ffmpeg_installed": ffmpeg_ok,
            "whisper_installed": whisper_ok,
            "mode": "live" if (ffmpeg_ok and whisper_ok) else "capability_reported_stem_grounded"
        }

    @classmethod
    def verify_dialogue_match(
        cls,
        expected_text: Optional[str] = None,
        asr_text: Optional[str] = None,
        metadata_dialogue: Optional[str] = None,
        observed_asr_text: Optional[str] = None,
        threshold: float = 0.65
    ) -> Any:
        """Calculates token overlap similarity between metadata dialogue and ASR transcript."""
        exp = expected_text if expected_text is not None else (metadata_dialogue or "")
        asr = asr_text if asr_text is not None else (observed_asr_text or "")

        if not exp and not asr:
            sim = 1.0
            is_match = True
        elif not exp or not asr:
            sim = 0.0
            is_match = False
        else:
            clean_exp = set(exp.lower().replace(".", "").replace(",", "").split())
            clean_asr = set(asr.lower().replace(".", "").replace(",", "").split())

            if not clean_exp:
                sim = 1.0
                is_match = True
            else:
                intersection = clean_exp.intersection(clean_asr)
                union = clean_exp.union(clean_asr)
                sim = len(intersection) / len(union) if union else 0.0

                if exp.lower() in asr.lower() or asr.lower() in exp.lower():
                    sim = max(sim, 0.95)
                is_match = (sim >= threshold)

        class MatchResult(tuple):
            def __getitem__(self, item):
                if isinstance(item, str):
                    if item == "match":
                        return is_match
                    if item in ["confidence", "similarity"]:
                        return sim
                return super().__getitem__(item)

        return MatchResult((is_match, sim))
