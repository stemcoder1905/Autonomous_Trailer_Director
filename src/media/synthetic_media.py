"""Synthetic media generator for deterministic testing and real video verification."""
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
from src.utils.logger import logger

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class SyntheticMediaGenerator:
    """Generates valid, real MP4 video files with stamped timecodes and visual labels for local testing."""

    @classmethod
    def create_synthetic_video(
        cls,
        output_path: Union[str, Path],
        duration_seconds: float = 120.0,
        fps: int = 24,
        width: int = 640,
        height: int = 360,
        scene_markers: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Renders an actual MP4 video file with visual scene cards and timecode stamps."""
        if not OPENCV_AVAILABLE:
            logger.warning("[SyntheticMediaGenerator] OpenCV unavailable; skipping video synthesis.")
            return False

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration_seconds * fps)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

        if not writer.isOpened():
            logger.error(f"[SyntheticMediaGenerator] Failed to open VideoWriter for '{out_path}'")
            return False

        markers = scene_markers or [
            {"scene_id": "scene_01", "start": 0.0, "end": 20.0, "label": "Dawn over Handlooms (Raghu & Dev)", "color": (40, 70, 30)},
            {"scene_id": "scene_02", "start": 20.0, "end": 45.0, "label": "Vikram Sedan Arrival (Confrontation)", "color": (30, 40, 80)},
            {"scene_id": "scene_03", "start": 45.0, "end": 70.0, "label": "Courtyard Chai Meeting (Dev & Meera)", "color": (50, 40, 40)},
            {"scene_id": "scene_04", "start": 70.0, "end": 95.0, "label": "Late Night Workshop Argument", "color": (20, 20, 50)},
            {"scene_id": "scene_05", "start": 95.0, "end": 120.0, "label": "Artisan Council Deliberation", "color": (40, 50, 60)},
        ]

        try:
            for frame_idx in range(total_frames):
                current_time = frame_idx / fps
                # Find matching scene
                current_marker = None
                for m in markers:
                    if m["start"] <= current_time < m["end"]:
                        current_marker = m
                        break

                if current_marker is None:
                    current_marker = {"scene_id": "scene_misc", "label": "Background footage", "color": (30, 30, 30)}

                # Create frame background
                base_color = current_marker.get("color", (40, 40, 40))
                frame = np.full((height, width, 3), base_color, dtype=np.uint8)

                # Draw timecode and labels
                mins = int(current_time // 60)
                secs = int(current_time % 60)
                msec = int((current_time - int(current_time)) * 1000)
                tc_str = f"{mins:02d}:{secs:02d}.{msec:03d}"

                # Title text
                scene_text = f"SCENE: {current_marker['scene_id'].upper()}"
                cv2.putText(frame, scene_text, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, current_marker.get("label", ""), (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 240), 1)
                cv2.putText(frame, f"TIMECODE: {tc_str}", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
                cv2.putText(frame, f"FPS: {fps} | FRAME: {frame_idx}/{total_frames}", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

                writer.write(frame)

            writer.release()
            logger.info(f"[SyntheticMediaGenerator] Generated test video: '{out_path}' ({duration_seconds}s, {total_frames} frames)")
            return True
        except Exception as e:
            writer.release()
            logger.error(f"[SyntheticMediaGenerator] Error creating synthetic video: {e}")
            return False
