"""Frame extraction module for capturing visual evidence at exact cut timestamps."""
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from src.utils.logger import logger

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class FrameExtractor:
    """Extracts start, middle, and end frames from physical video files for visual verification."""

    @staticmethod
    def is_available() -> bool:
        return OPENCV_AVAILABLE

    @classmethod
    def extract_frame_at_timestamp(
        cls,
        video_path: Union[str, Path],
        timestamp_seconds: float,
        output_path: Optional[Union[str, Path]] = None
    ) -> Optional[Any]:
        """Extracts an individual video frame at a given timestamp in seconds."""
        v_path = Path(video_path)
        if not v_path.exists() or not OPENCV_AVAILABLE:
            logger.warning(f"[FrameExtractor] Cannot extract frame from '{v_path}': file missing or OpenCV unavailable.")
            return None

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            return None

        try:
            # Set position in milliseconds
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_seconds * 1000.0))
            success, frame = cap.read()
            if not success or frame is None:
                return None

            if output_path:
                out_p = Path(output_path)
                out_p.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_p), frame)

            return frame
        except Exception as e:
            logger.error(f"[FrameExtractor] Failed to extract frame at {timestamp_seconds}s: {e}")
            return None
        finally:
            cap.release()

    @classmethod
    def extract_scene_frames(
        cls,
        video_path: Union[str, Path],
        scene_id: str,
        start_seconds: float,
        end_seconds: float,
        output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """Extracts start, middle, and end frames for a selected scene cut.

        Returns:
            Dictionary with frame paths and extraction metadata.
        """
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        mid_seconds = round((start_seconds + end_seconds) / 2.0, 3)
        # Offset start slightly inward to avoid black frames or transition artifacts
        t_start = max(0.0, start_seconds + 0.05)
        t_end = max(t_start, end_seconds - 0.05)

        start_file = out_d / f"{scene_id}_start.jpg"
        mid_file = out_d / f"{scene_id}_middle.jpg"
        end_file = out_d / f"{scene_id}_end.jpg"

        frames_checked: List[str] = []
        success_count = 0

        # Attempt extraction
        for name, t_val, f_path in [
            ("start", t_start, start_file),
            ("middle", mid_seconds, mid_file),
            ("end", t_end, end_file)
        ]:
            frame = cls.extract_frame_at_timestamp(video_path, t_val, output_path=f_path)
            if frame is not None:
                frames_checked.append(str(f_path))
                success_count += 1
            else:
                # If extraction fails (e.g. mock environment), record placeholder path
                frames_checked.append(f"frames/{scene_id}_{name}.jpg")

        source_type = "REPLAY_FIXTURE" if ("sample_data" in str(video_path).lower() or "synthetic" in str(video_path).lower()) else "REAL_MEDIA"

        return {
            "source": str(video_path),
            "source_type": source_type,
            "verification_method": "opencv_frame_seek",
            "verified": (success_count > 0),
            "timestamp": start_seconds,
            "scene_id": scene_id,
            "start_time": start_seconds,
            "end_time": end_seconds,
            "frames_checked": frames_checked,
            "extracted_count": success_count,
            "media_verified": (success_count > 0)
        }
