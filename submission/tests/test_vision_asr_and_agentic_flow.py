"""Test 19: Comprehensive verification of Vision, ASR, Candidate Selection, and Media Grounding."""
import wave
import struct
from pathlib import Path
import pytest
from src.providers.vision import VisionProviderManager, MockVisionProvider, LiveVisionProvider
from src.providers.asr import ASRProviderManager, MockASRProvider, LiveASRProvider
from src.providers.llm import ProviderManager
from src.agents.planner_agent import CreativeTrailerPlannerAgent
from src.agents.audience_agent import AudienceStrategyAgent
from src.agents.story_agent import StoryUnderstandingAgent
from src.agents.constraint_agent import ConstraintAnalysisAgent
from src.agents.validator_agent import IndependentValidationAgent
from src.media.media_validator import MediaValidator
from src.models.schemas import TrailerSegment, SceneMetadata
from src.models.enums import AudienceType, ValidationStatus, SourceType
from src.ingestion.episode_loader import EpisodePackageLoader


@pytest.fixture
def temp_wav_file(tmp_path):
    """Generate a minimal valid 1-second sine wave WAV file for testing audio detection."""
    wav_path = tmp_path / "test_audio.wav"
    sample_rate = 16000
    num_frames = sample_rate
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = struct.pack(f"<{num_frames}h", *([0] * num_frames))
        wf.writeframes(frames)
    return wav_path


@pytest.fixture
def package_and_maps():
    base_dir = Path("sample_data")
    loader = EpisodePackageLoader(base_dir)
    package = loader.load_package()

    story_agent = StoryUnderstandingAgent()
    story_map = story_agent.analyze_story(package)

    constraint_agent = ConstraintAnalysisAgent()
    constraint_map = constraint_agent.analyze_constraints(package, reference_date="2026-02-15")

    return package, story_map, constraint_map


# -------------------------------------------------------------
# 1. Vision Provider Tests
# -------------------------------------------------------------

def test_mock_vision_provider_supported_claim():
    vision_mgr = VisionProviderManager(preferred_provider="mock")
    res = vision_mgr.verify_frame(
        frame_path="sample_run/frames/scene_01_middle.jpg",
        claim="Master Dev inspecting traditional wooden handloom in workshop",
        scene_id="scene_01",
        timestamp="00:01:15.000",
        expected_characters=["Dev"],
        source_type=SourceType.REPLAY_FIXTURE
    )
    assert res.status == "PASS"
    assert res.supported is True
    assert res.contradicted is False
    assert res.confidence >= 0.75
    assert res.source_type == SourceType.REPLAY_FIXTURE.value


def test_mock_vision_provider_contradicted_claim():
    vision_mgr = VisionProviderManager(preferred_provider="mock")
    res = vision_mgr.verify_frame(
        frame_path="sample_run/frames/scene_01_middle.jpg",
        claim="An explosion of an alien spaceship in deep space",
        scene_id="scene_01",
        timestamp="00:01:15.000",
        expected_characters=["Dev"]
    )
    assert res.status == "FAIL"
    assert res.supported is False
    assert res.contradicted is True


def test_mock_vision_provider_low_confidence_review():
    vision_mgr = VisionProviderManager(preferred_provider="mock")
    res = vision_mgr.verify_frame(
        frame_path="sample_run/frames/scene_01_middle.jpg",
        claim="An ambiguous low_confidence silhouette in darkness",
        scene_id="scene_01",
        timestamp="00:01:15.000"
    )
    assert res.status == "REVIEW"
    assert res.confidence < 0.75


def test_live_vision_provider_fallback():
    vision_mgr = VisionProviderManager(preferred_provider="live", simulate_failure=True)
    res = vision_mgr.verify_frame(
        frame_path="sample_run/frames/scene_01_middle.jpg",
        claim="Master Dev working in handloom workshop",
        scene_id="scene_01"
    )
    assert res.status in ["PASS", "REVIEW", "FAIL"]
    assert vision_mgr.last_provenance["fallback_used"] is True
    assert vision_mgr.last_provenance["source_type"] == SourceType.MOCK_MODEL.value


# -------------------------------------------------------------
# 2. ASR Provider Tests
# -------------------------------------------------------------

def test_mock_asr_provider_matching_dialogue(temp_wav_file):
    asr_mgr = ASRProviderManager(preferred_provider="mock")
    res = asr_mgr.transcribe(
        audio_or_video_path=temp_wav_file,
        start_seconds=0.0,
        end_seconds=1.0,
        reference_dialogue="Our looms have sung this rhythm for three centuries."
    )
    assert res.audio_status == "AUDIO_STREAM_DETECTED"
    assert res.metadata_match is True
    assert res.metadata_divergence_score == 0.0
    assert len(res.segments) > 0


def test_mock_asr_provider_divergent_dialogue(temp_wav_file):
    asr_mgr = ASRProviderManager(preferred_provider="mock")
    res = asr_mgr.transcribe(
        audio_or_video_path=temp_wav_file,
        start_seconds=0.0,
        end_seconds=1.0,
        reference_dialogue="Corrupted and mismatched dialogue subtitle"
    )
    assert res.metadata_match is False
    assert res.metadata_divergence_score > 0.5


def test_asr_provider_audio_not_available():
    asr_mgr = ASRProviderManager(preferred_provider="mock")
    # episode_01.mp4 has no audio track, so it accurately reports AUDIO_STREAM_NOT_AVAILABLE
    res = asr_mgr.transcribe(
        audio_or_video_path="sample_data/media/episode_01.mp4",
        start_seconds=60.0,
        end_seconds=75.0,
        reference_dialogue="Any dialogue"
    )
    assert res.audio_status == "AUDIO_STREAM_NOT_AVAILABLE"
    assert res.is_asr_output is False
    assert res.transcript_text == "AUDIO_STREAM_NOT_AVAILABLE"


# -------------------------------------------------------------
# 3. ProviderManager Provenance Metadata
# -------------------------------------------------------------

def test_llm_provider_manager_fallback_provenance():
    mgr = ProviderManager(preferred_provider="primary", simulate_primary_failure=True)
    res = mgr.generate("Plan trailer for family")
    assert len(res) > 0
    assert mgr.active_provider_name == "mock"
    prov = mgr.get_provenance()
    assert prov["fallback_used"] is True
    assert prov["source_type"] == "MOCK_MODEL"
    assert "mock" in prov["model"].lower()


# -------------------------------------------------------------
# 4. Independent Candidate Selection
# -------------------------------------------------------------

def test_planner_select_best_candidate(package_and_maps):
    package, story_map, constraint_map = package_and_maps
    planner = CreativeTrailerPlannerAgent()
    audience_agent = AudienceStrategyAgent()
    validator = IndependentValidationAgent()

    brief = audience_agent.create_strategy(
        AudienceType.YOUNG_ADULT, package, story_map, constraint_map
    )

    candidates = planner.generate_candidate_plans(
        brief, package, story_map, constraint_map, num_candidates=3
    )
    assert len(candidates) == 3

    # select_best_candidate evaluates candidates via validator
    best = planner.select_best_candidate(candidates, validator, package, story_map, constraint_map)
    assert best is not None
    assert best.audience == AudienceType.YOUNG_ADULT.value
    assert len(best.segments) > 0


# -------------------------------------------------------------
# 5. MediaValidator Multimodal Verification Integration
# -------------------------------------------------------------

def test_media_validator_visual_claim_verification():
    mv = MediaValidator(media_path="sample_data/media/episode_01.mp4", mode="REPLAY")
    
    seg = TrailerSegment(
        segment_id="seg_01",
        source_in="00:01:00.000",
        source_out="00:01:10.000",
        scene_id="scene_01",
        video="scene_01",
        audio="dialogue_01",
        reason="Dev weaving at traditional loom",
        evidence=[]
    )
    scene = SceneMetadata(
        scene_id="scene_01",
        start_time="00:01:00.000",
        end_time="00:02:00.000",
        duration_seconds=60.0,
        description="Dev weaving silk at the ancestral loom",
        characters=["Dev"],
        dialogue_ids=[],
        subtitle_ids=[],
        emotion="determined"
    )

    # Standard supported claim
    res = mv.verify_visual_claim(seg, scene)
    assert res["status"] in ["PASS", "PASS_WITH_WARNINGS"]
    assert res["confidence"] >= 0.75

    # Contradicted claim (contains explosion)
    scene_contradicted = SceneMetadata(
        scene_id="scene_01",
        start_time="00:01:00.000",
        end_time="00:02:00.000",
        duration_seconds=60.0,
        description="Alien spaceship explosion in low orbit",
        characters=["Dev"],
        dialogue_ids=[],
        subtitle_ids=[],
        emotion="terror"
    )
    res_fail = mv.verify_visual_claim(seg, scene_contradicted)
    assert res_fail["status"] == "FAIL"
    assert res_fail["visual_match"] is False
