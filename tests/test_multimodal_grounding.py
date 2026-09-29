"""Unit and integration tests for multimodal grounding, visual claim verification, and repair."""
from pathlib import Path
import pytest
from src.media.media_validator import MediaValidator
from src.media.audio_processor import AudioProcessor
from src.models.schemas import TrailerPlan, TrailerSegment, SceneMetadata, SpoilerLevel
from src.models.enums import ValidationStatus, AudienceType
from src.agents.validator_agent import IndependentValidationAgent
from src.agents.repair_agent import RepairAgent
from src.agents.audience_agent import AudienceStrategyAgent, AudienceStrategyBrief
from src.agents.planner_agent import CreativeTrailerPlannerAgent
from src.ingestion.episode_loader import EpisodePackageLoader
from src.agents.story_agent import StoryUnderstandingAgent
from src.agents.constraint_agent import ConstraintAnalysisAgent


def test_visual_claim_mismatch_rejection():
    """Verify MediaValidator rejects visual claim contradictions with SOURCE_ACCURACY = FAIL."""
    validator = MediaValidator()

    # Canon scene: heated hostile confrontation between Singhania and weavers
    scene = SceneMetadata(
        scene_id="scene_02",
        start_time="00:02:10.000",
        end_time="00:04:10.000",
        duration_seconds=120.0,
        description="Singhania arrives with buyout ultimatum; heated hostile confrontation with master weavers.",
        characters=["Singhania", "Brijesh"],
        emotion="confrontation",
        spoiler_level=SpoilerLevel.NONE
    )

    # Segment reason falsely claims tender 'Mother hugs daughter'
    mismatched_segment = TrailerSegment(
        segment_id="seg_mismatch_01",
        source_in="00:02:15.000",
        source_out="00:02:25.000",
        scene_id="scene_02",
        video="scene_02",
        audio="audio_02",
        reason="Mother hugs daughter in warm emotional embrace",
        evidence=["scene:scene_02"]
    )

    results = validator.validate_segment_media(mismatched_segment, scene=scene)
    assert any(
        r.status == ValidationStatus.FAIL and "visual claim mismatch" in r.message.lower()
        for r in results
    ), "Expected validator to reject contradictory visual claim"


def test_visual_mismatch_repair_and_pass():
    """Verify that when a visual mismatch is detected, RepairAgent replaces the clip and re-validation passes."""
    base_dir = Path("sample_data")
    loader = EpisodePackageLoader(base_dir)
    package = loader.load_package()

    story_agent = StoryUnderstandingAgent()
    story_map = story_agent.analyze_story(package)

    constraint_agent = ConstraintAnalysisAgent()
    constraint_map = constraint_agent.analyze_constraints(package, reference_date="2026-02-15")

    planner = CreativeTrailerPlannerAgent()
    audience_agent = AudienceStrategyAgent()
    brief = audience_agent.create_strategy(
        AudienceType.FAMILY, package, story_map, constraint_map
    )

    # Generate visual mismatch adversarial plan
    adversarial_plan = planner.plan_trailer(
        brief, package, story_map, constraint_map, adversarial_scenario="visual_mismatch"
    )

    # Validate plan with IndependentValidationAgent -> Must FAIL
    validator = IndependentValidationAgent()
    initial_report = validator.validate_plan(adversarial_plan, package, story_map, constraint_map)
    assert initial_report.status == ValidationStatus.FAIL

    # RepairAgent repairs the plan
    repair_agent = RepairAgent(validator_agent=validator)
    repaired_plan, passed = repair_agent.attempt_repair(
        adversarial_plan, package, story_map, constraint_map
    )

    assert passed is True
    assert repaired_plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
    # Check that problematic scene was replaced with a valid grounded scene
    assert repaired_plan.segments[0].scene_id != "scene_02"


def test_multimodal_evidence_traceability():
    """Verify that planned segments contain complete multimodal evidence structures."""
    base_dir = Path("sample_data")
    loader = EpisodePackageLoader(base_dir)
    package = loader.load_package()

    story_agent = StoryUnderstandingAgent()
    story_map = story_agent.analyze_story(package)

    constraint_agent = ConstraintAnalysisAgent()
    constraint_map = constraint_agent.analyze_constraints(package, reference_date="2026-02-15")

    planner = CreativeTrailerPlannerAgent()
    audience_agent = AudienceStrategyAgent()
    brief = audience_agent.create_strategy(
        AudienceType.FAMILY, package, story_map, constraint_map
    )

    plan = planner.plan_trailer(brief, package, story_map, constraint_map)
    validator = IndependentValidationAgent()
    validator.validate_plan(plan, package, story_map, constraint_map)

    for seg in plan.segments:
        assert seg.source is not None
        assert seg.frame_evidence is not None and len(seg.frame_evidence) > 0
        assert seg.rights_evidence is not None
        assert seg.validation_status_map is not None
        assert "media" in seg.validation_status_map
        assert "source" in seg.validation_status_map


def test_dialogue_verification():
    """Verify AudioProcessor verifies matching dialogue and flags mismatches."""
    matching = AudioProcessor.verify_dialogue_match(
        metadata_dialogue="Our looms have sung this rhythm for three centuries, Dev.",
        observed_asr_text="Our looms have sung this rhythm for three centuries, Dev."
    )
    assert matching["match"] is True
    assert matching["confidence"] >= 0.95

    mismatch = AudioProcessor.verify_dialogue_match(
        metadata_dialogue="Our looms have sung this rhythm for three centuries, Dev.",
        observed_asr_text="Completely unrelated dialogue about something else entirely."
    )
    assert mismatch["match"] is False
    assert mismatch["confidence"] < 0.5
