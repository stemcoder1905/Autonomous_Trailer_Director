"""Real video metadata extraction and boundary validation using OpenCV."""
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union
from pydantic import BaseModel, Field
from src.models.enums import SourceType
from src.utils.logger import logger

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("[VideoProcessor] OpenCV is not installed; video extraction will run in capability-reported mode.")


class VideoMetadata(BaseModel):
    """Structured video technical parameters."""
    path: str
    fps: float = 0.0
    frame_count: int = 0
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    codec: str = "unknown"
    is_valid: bool = False
    has_video_stream: bool = False
    source_type: SourceType = SourceType.REPLAY_FIXTURE
    verification_method: str = "opencv_inspection"
    error_message: Optional[str] = None


class VideoProcessor:
    """Extracts video parameters and enforces strict media duration boundaries."""

    @staticmethod
    def is_available() -> bool:
        """Returns True if OpenCV is present in the environment."""
        return OPENCV_AVAILABLE

    @classmethod
    def get_source_type(cls, video_path: Union[str, Path]) -> SourceType:
        """Determines whether video is the synthetic replay fixture or an external real media file."""
        v_str = str(video_path).replace("\\", "/").lower()
        if "sample_data/media/episode_01.mp4" in v_str or "sample_data" in v_str or "synthetic" in v_str:
            return SourceType.REPLAY_FIXTURE
        return SourceType.REAL_MEDIA

    @classmethod
    def detect_video_stream(cls, video_path: Union[str, Path]) -> Tuple[bool, Dict[str, Any]]:
        """Inspects whether a valid video stream is present in the media container."""
        v_path = Path(video_path)
        source_type = cls.get_source_type(v_path)
        if not v_path.exists():
            return False, {
                "source": str(v_path),
                "source_type": source_type.value,
                "verification_method": "opencv_inspection",
                "verified": False,
                "error": f"Video file not found at '{v_path}'"
            }

        if not OPENCV_AVAILABLE:
            return False, {
                "source": str(v_path),
                "source_type": source_type.value,
                "verification_method": "opencv_inspection",
                "verified": False,
                "error": "OpenCV is not installed"
            }

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            return False, {
                "source": str(v_path),
                "source_type": source_type.value,
                "verification_method": "opencv_inspection",
                "verified": False,
                "error": f"Failed to open video container at '{v_path}'"
            }

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            has_stream = bool(width > 0 and height > 0 and frames > 0)
            return has_stream, {
                "source": str(v_path),
                "source_type": source_type.value,
                "verification_method": "opencv_inspection",
                "verified": has_stream,
                "width": width,
                "height": height,
                "frame_count": frames,
                "fps": round(fps, 3),
                "duration_seconds": round(frames / fps, 3) if fps > 0 else 0.0
            }
        finally:
            cap.release()

    @classmethod
    def extract_metadata(cls, video_path: Union[str, Path]) -> VideoMetadata:
        """Inspects video container using OpenCV to detect FPS, frame count, resolution, and duration."""
        v_path = Path(video_path)
        source_type = cls.get_source_type(v_path)

        if not v_path.exists():
            return VideoMetadata(
                path=str(v_path),
                is_valid=False,
                has_video_stream=False,
                source_type=source_type,
                error_message=f"Video file does not exist at '{v_path}'"
            )

        if not OPENCV_AVAILABLE:
            return VideoMetadata(
                path=str(v_path),
                is_valid=False,
                has_video_stream=False,
                source_type=source_type,
                error_message="OpenCV is not installed; cannot inspect physical video frames."
            )

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            return VideoMetadata(
                path=str(v_path),
                is_valid=False,
                has_video_stream=False,
                source_type=source_type,
                error_message=f"Failed to open video container at '{v_path}'"
            )

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)]).strip()

            duration = round(frame_count / fps, 3) if fps > 0 else 0.0
            has_stream = bool(width > 0 and height > 0 and frame_count > 0)

            return VideoMetadata(
                path=str(v_path),
                fps=round(fps, 3),
                frame_count=frame_count,
                duration_seconds=duration,
                width=width,
                height=height,
                codec=codec or "mp4v",
                is_valid=has_stream,
                has_video_stream=has_stream,
                source_type=source_type,
                verification_method="opencv_inspection"
            )
        except Exception as e:
            return VideoMetadata(
                path=str(v_path),
                is_valid=False,
                has_video_stream=False,
                source_type=source_type,
                error_message=f"Error inspecting video stream: {str(e)}"
            )
        finally:
            cap.release()

    @classmethod
    def validate_timestamp(
        cls,
        video_path: Union[str, Path],
        timestamp_seconds: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Verifies if a specific cut timestamp resides strictly within physical media duration."""
        meta = cls.extract_metadata(video_path)
        evidence = {
            "video_path": str(video_path),
            "timestamp": timestamp_seconds,
            "media_duration": meta.duration_seconds,
            "fps": meta.fps,
            "media_verified": meta.is_valid
        }

        if not meta.is_valid:
            return False, f"Media inspection failed: {meta.error_message}", evidence

        if timestamp_seconds < 0.0:
            return False, f"Timestamp {timestamp_seconds}s is negative (invalid media bound).", evidence

        if timestamp_seconds > meta.duration_seconds:
            return (
                False,
                f"Timestamp {timestamp_seconds}s exceeds actual video duration of {meta.duration_seconds}s.",
                evidence
            )

        return True, f"Timestamp {timestamp_seconds}s verified within media duration.", evidence

    @classmethod
    def validate_segment_bounds(
        cls,
        video_path: Union[str, Path],
        start_sec: float,
        end_sec: float
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Verifies that start < end and both timestamps are within physical media boundaries."""
        meta = cls.extract_metadata(video_path)
        evidence = {
            "video_path": str(video_path),
            "start_time": start_sec,
            "end_time": end_sec,
            "media_duration": meta.duration_seconds,
            "fps": meta.fps,
            "media_verified": meta.is_valid
        }

        if not meta.is_valid:
            return False, f"Media inspection failed: {meta.error_message}", evidence

        if start_sec >= end_sec:
            return False, f"Inverted cut range: start_time ({start_sec}s) >= end_time ({end_sec}s).", evidence

        if start_sec < 0.0:
            return False, f"Negative start time: {start_sec}s.", evidence

        if end_sec > meta.duration_seconds:
            return (
                False,
                f"Cut end time ({end_sec}s) exceeds media duration ({meta.duration_seconds}s).",
                evidence
            )

        return True, f"Cut range ({start_sec}s - {end_sec}s) verified within media bounds.", evidence

    @classmethod
    def validate_segment_boundaries(
        cls,
        video_path: Union[str, Path],
        start_sec: float,
        end_sec: float
    ) -> Dict[str, Any]:
        """Convenience method returning dictionary result for boundary validation."""
        valid, reason, evidence = cls.validate_segment_bounds(video_path, start_sec, end_sec)
        return {"valid": valid, "reason": reason, "evidence": evidence}

    @classmethod
    def detect_shot_boundaries(
        cls,
        video_path: Union[str, Path],
        threshold: float = 30.0,
        sample_step_frames: int = 5
    ) -> list:
        """Detect shot transitions / visual cuts using frame difference analysis in OpenCV.
        
        Returns a list of detected cut timestamps with confidence and frame indices.
        """
        cuts = []
        if not OPENCV_AVAILABLE:
            return cuts

        v_path = Path(video_path)
        if not v_path.exists():
            return cuts

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            return cuts

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
            prev_gray = None
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_step_frames == 0:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (160, 90))

                    if prev_gray is not None:
                        diff = cv2.absdiff(prev_gray, gray)
                        mean_diff = float(diff.mean())
                        if mean_diff > threshold:
                            timestamp_sec = round(frame_idx / fps, 3)
                            cuts.append({
                                "frame_index": frame_idx,
                                "timestamp_seconds": timestamp_sec,
                                "mean_pixel_diff": round(mean_diff, 2),
                                "cut_type": "HARD_CUT" if mean_diff > threshold * 1.5 else "TRANSITION"
                            })
                    prev_gray = gray
                frame_idx += 1
        finally:
            cap.release()

        return cuts
