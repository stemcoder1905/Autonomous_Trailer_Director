"""Unit and integration tests for media processing, video boundary validation, and frame extraction."""
from pathlib import Path
import pytest
from src.media.video_processor import VideoProcessor, VideoMetadata
from src.media.frame_extractor import FrameExtractor
from src.media.audio_processor import AudioProcessor
from src.media.media_validator import MediaValidator
from src.models.schemas import TrailerSegment, SceneMetadata, SpoilerLevel
from src.models.enums import ValidationStatus, Severity


def test_video_processor_metadata():
    """Verify VideoProcessor extracts valid metadata from physical test video."""
    video_path = Path("sample_data/media/episode_01.mp4")
    assert video_path.exists(), "episode_01.mp4 must exist for media processing tests"

    meta = VideoProcessor.extract_metadata(video_path)
    assert isinstance(meta, VideoMetadata)
    assert meta.duration_seconds > 0
    assert meta.fps > 0
    assert meta.width > 0
    assert meta.height > 0
    assert meta.frame_count > 0


def test_video_processor_boundary_validation():
    """Verify segment boundary validation detects cuts exceeding media length."""
    video_path = Path("sample_data/media/episode_01.mp4")
    meta = VideoProcessor.extract_metadata(video_path)

    # Valid cut
    valid_res = VideoProcessor.validate_segment_boundaries(video_path, 10.0, 30.0)
    assert valid_res["valid"] is True

    # Invalid cut: starts or ends beyond physical video duration
    overshoot_end = meta.duration_seconds + 500.0
    invalid_res = VideoProcessor.validate_segment_boundaries(video_path, 10.0, overshoot_end)
    assert invalid_res["valid"] is False
    assert "exceeds" in invalid_res["reason"].lower()


def test_frame_extractor():
    """Verify FrameExtractor extracts start, middle, and end frames to disk."""
    video_path = Path("sample_data/media/episode_01.mp4")
    output_dir = Path("sample_run/frames")

    res = FrameExtractor.extract_scene_frames(
        video_path=video_path,
        scene_id="test_scene_01",
        start_seconds=5.0,
        end_seconds=15.0,
        output_dir=output_dir
    )

    assert "frames_checked" in res
    assert len(res["frames_checked"]) == 3
    for frame_file in res["frames_checked"]:
        assert Path(frame_file).exists()


def test_audio_processor_capability_status():
    """Verify AudioProcessor provides capability status and does not crash when FFmpeg/Whisper are missing."""
    status = AudioProcessor.get_capability_status()
    assert "ffmpeg_installed" in status
    assert "whisper_installed" in status
    assert "mode" in status
    assert isinstance(status["ffmpeg_installed"], bool)


def test_media_duration_validator_rejection():
    """Verify MediaValidator rejects segments that cut beyond physical media duration."""
    validator = MediaValidator(media_dir="sample_data/media")
    video_path = Path("sample_data/media/episode_01.mp4")
    meta = VideoProcessor.extract_metadata(video_path)

    # Segment with cut exceeding physical duration
    overshoot_time = f"01:00:00.000"  # 3600 seconds, > 1350s media
    bad_segment = TrailerSegment(
        segment_id="seg_overshoot",
        source_in="00:00:10.000",
        source_out=overshoot_time,
        scene_id="scene_01",
        video="scene_01",
        audio="music_01",
        reason="Test cut that overshoots physical duration",
        evidence=["scene:scene_01"]
    )

    results = validator.validate_segment_media(bad_segment)
    assert any(r.status == ValidationStatus.FAIL and "duration" in r.message.lower() for r in results)
