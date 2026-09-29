"""Tests for honest and reusable media input architecture.

Covers:
1. Valid video input
2. Invalid video path
3. Video duration accuracy
4. Timestamp boundary validation
5. Frame extraction with provenance
6. Audio stream detection
7. No-audio handling (AUDIO_STREAM_NOT_AVAILABLE)
8. Evidence provenance across REPLAY and REAL_MEDIA modes
"""
import wave
import struct
from pathlib import Path
import pytest

from src.media.video_processor import VideoProcessor, VideoMetadata
from src.media.audio_processor import AudioProcessor
from src.media.frame_extractor import FrameExtractor
from src.media.media_validator import MediaValidator
from src.models.enums import SourceType, ValidationStatus
from src.models.schemas import (
    TrailerSegment,
    SceneMetadata,
    MediaEvidence,
    SegmentSourceEvidence,
    DialogueEvidence
)


@pytest.fixture
def replay_video_path():
    p = Path("sample_data/media/episode_01.mp4")
    assert p.exists(), "Replay video fixture must exist"
    return p


@pytest.fixture
def temp_wav_file(tmp_path):
    """Generate a minimal valid 1-second sine wave WAV file for testing audio detection."""
    wav_path = tmp_path / "test_audio.wav"
    sample_rate = 16000
    num_frames = sample_rate  # 1 second
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Write silence / low tone
        frames = struct.pack(f"<{num_frames}h", *([0] * num_frames))
        wf.writeframes(frames)
    return wav_path


# 1. Valid video input
def test_valid_video_input(replay_video_path):
    meta = VideoProcessor.extract_metadata(replay_video_path)
    assert meta.is_valid is True
    assert meta.has_video_stream is True
    assert meta.fps > 0
    assert meta.width > 0
    assert meta.height > 0
    assert meta.frame_count > 0
    assert meta.duration_seconds > 0
    assert meta.source_type == SourceType.REPLAY_FIXTURE
    assert meta.verification_method == "opencv_inspection"


# 2. Invalid video path
def test_invalid_video_path():
    invalid_path = Path("sample_data/media/non_existent_file_xyz.mp4")
    meta = VideoProcessor.extract_metadata(invalid_path)
    assert meta.is_valid is False
    assert meta.has_video_stream is False
    assert meta.duration_seconds == 0.0
    assert meta.frame_count == 0
    assert "does not exist" in (meta.error_message or "").lower()


# 3. Video duration
def test_video_duration_accuracy(replay_video_path):
    meta = VideoProcessor.extract_metadata(replay_video_path)
    expected_duration = round(meta.frame_count / meta.fps, 3)
    assert abs(meta.duration_seconds - expected_duration) < 0.1
    assert meta.duration_seconds > 10.0  # Synthetic fixture is at least ~60s


# 4. Timestamp validation
def test_timestamp_validation(replay_video_path):
    meta = VideoProcessor.extract_metadata(replay_video_path)
    
    # In-bounds timestamp range
    valid_res = VideoProcessor.validate_segment_boundaries(replay_video_path, 2.0, 10.0)
    assert valid_res["valid"] is True
    assert valid_res["evidence"]["start_time"] == 2.0
    assert valid_res["evidence"]["end_time"] == 10.0

    # Negative start timestamp
    neg_res = VideoProcessor.validate_segment_boundaries(replay_video_path, -1.0, 10.0)
    assert neg_res["valid"] is False
    assert "negative" in neg_res["reason"].lower()

    # Inverted timestamps (start >= end)
    inv_res = VideoProcessor.validate_segment_boundaries(replay_video_path, 15.0, 10.0)
    assert inv_res["valid"] is False
    assert ">=" in inv_res["reason"] or "inverted" in inv_res["reason"].lower()

    # Out-of-bounds end timestamp exceeding video duration
    overshoot_end = meta.duration_seconds + 50.0
    out_res = VideoProcessor.validate_segment_boundaries(replay_video_path, 5.0, overshoot_end)
    assert out_res["valid"] is False
    assert "exceeds media duration" in out_res["reason"].lower()


# 5. Frame extraction
def test_frame_extraction_with_provenance(replay_video_path, tmp_path):
    output_dir = tmp_path / "frames"
    res = FrameExtractor.extract_scene_frames(
        video_path=replay_video_path,
        scene_id="scene_01",
        start_seconds=2.0,
        end_seconds=6.0,
        output_dir=output_dir
    )

    assert "frames_checked" in res
    assert len(res["frames_checked"]) == 3
    for frame_file in res["frames_checked"]:
        assert Path(frame_file).exists()

    # Verify provenance fields returned by FrameExtractor
    assert res["source_type"] == SourceType.REPLAY_FIXTURE
    assert res["verification_method"] == "opencv_frame_seek"
    assert res["verified"] is True
    assert "timestamp" in res


# 6. Audio stream detection
def test_audio_stream_detection(temp_wav_file):
    has_audio, status = AudioProcessor.detect_audio_stream(temp_wav_file)
    assert has_audio is True
    assert "AUDIO_STREAM_DETECTED" in status


# 7. No-audio handling
def test_no_audio_handling(replay_video_path, tmp_path):
    # Replay fixture was created via OpenCV without an audio track
    has_audio, status = AudioProcessor.detect_audio_stream(replay_video_path)
    assert has_audio is False
    assert status == "AUDIO_STREAM_NOT_AVAILABLE"

    # Attempting to extract audio must cleanly return False without crashing
    out_wav = tmp_path / "extracted.wav"
    success, extract_msg = AudioProcessor.extract_audio(replay_video_path, out_wav)
    assert success is False
    assert extract_msg == "AUDIO_STREAM_NOT_AVAILABLE"

    # ASR must never claim metadata is ASR output
    asr_res = AudioProcessor.transcribe_segment(replay_video_path, 0.0, 5.0)
    assert asr_res["is_asr_output"] is False
    assert asr_res["asr_engine"] == "NONE"
    assert asr_res["audio_status"] == "AUDIO_STREAM_NOT_AVAILABLE"
    assert "AUDIO_STREAM_NOT_AVAILABLE" in asr_res["note"]


# 8. Evidence provenance
def test_evidence_provenance(replay_video_path):
    # Test REPLAY mode
    replay_validator = MediaValidator(media_path=replay_video_path, mode="REPLAY")
    seg = TrailerSegment(
        segment_id="seg_prov_01",
        source_in="00:00:05.000",
        source_out="00:00:10.000",
        scene_id="scene_01",
        video="episode_01.mp4",
        audio="dialogue",
        dialogue="Our looms have sung this rhythm for three centuries.",
        dialogue_id="dial_01",
        subtitle="Our looms have sung this rhythm for three centuries.",
        subtitle_id="sub_01",
        reason="Testing provenance",
        evidence=["scene:scene_01"]
    )
    sc = SceneMetadata(
        scene_id="scene_01",
        start_time="00:00:00.000",
        end_time="00:00:30.000",
        duration_seconds=30.0,
        description="Heritage workshop scene",
        emotion="reflective",
        characters=["Dev", "Father"]
    )

    results = replay_validator.validate_segment_media(seg, sc)
    assert len(results) == 0  # 0 violations = passed

    # Check segment source evidence provenance
    assert isinstance(seg.source, SegmentSourceEvidence)
    assert seg.source.source_type == SourceType.REPLAY_FIXTURE
    assert seg.source.verification_method == "opencv_inspection"
    assert seg.source.verified is True
    assert seg.source.timestamp is not None

    # Check dialogue evidence provenance (must NEVER claim to be ASR output)
    assert isinstance(seg.dialogue_evidence, DialogueEvidence)
    assert seg.dialogue_evidence.source_type == SourceType.METADATA
    assert seg.dialogue_evidence.is_asr_output is False
    assert seg.dialogue_evidence.asr_engine in ["NOT_PERFORMED", "NONE"]
    assert seg.dialogue_evidence.audio_status == "AUDIO_STREAM_NOT_AVAILABLE"
    assert seg.dialogue_evidence.verified is True

    # Test REAL_MEDIA mode
    real_validator = MediaValidator(media_path=replay_video_path, mode="REAL_MEDIA")
    seg_real = TrailerSegment(
        segment_id="seg_prov_02",
        source_in="00:00:05.000",
        source_out="00:00:10.000",
        scene_id="scene_01",
        video="episode_01.mp4",
        audio="dialogue",
        dialogue="Testing real media mode",
        dialogue_id="dial_01",
        subtitle="Testing real media mode",
        subtitle_id="sub_01",
        reason="Testing real media mode provenance",
        evidence=["scene:scene_01"]
    )
    real_results = real_validator.validate_segment_media(seg_real, sc)
    assert len(real_results) == 0
    assert seg_real.source.source_type == SourceType.REAL_MEDIA
    assert seg_real.source.verification_method == "opencv_inspection"
    assert seg_real.source.verified is True
