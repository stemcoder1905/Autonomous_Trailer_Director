"""Unit and integration tests for agentic candidate planning, live provider schema, and human approval."""
from pathlib import Path
import pytest
from src.models.schemas import (
    TrailerPlan,
    TrailerSegment,
    ValidationResultItem,
    SpoilerMap,
    TrailerValidationReport,
)
from src.models.enums import ValidationStatus, Severity, RepairAction, AudienceType
from src.agents.planner_agent import CreativeTrailerPlannerAgent
from src.agents.audience_agent import AudienceStrategyAgent, AudienceStrategyBrief
from src.agents.story_agent import StoryUnderstandingAgent
from src.agents.constraint_agent import ConstraintAnalysisAgent
from src.agents.repair_agent import RepairAgent
from src.agents.validator_agent import IndependentValidationAgent
from src.ingestion.episode_loader import EpisodePackageLoader
from src.providers.live import LiveLLMProvider


def test_generate_candidate_plans():
    """Verify CreativeTrailerPlannerAgent generates multiple distinct candidate plans with diverse pacing/strategy."""
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
        AudienceType.YOUNG_ADULT, package, story_map, constraint_map
    )

    candidates = planner.generate_candidate_plans(
        brief, package, story_map, constraint_map, num_candidates=3
    )

    assert len(candidates) == 3
    # Check that candidate IDs and creative strategies differ
    candidate_ids = [c.trailer_id for c in candidates]
    assert len(set(candidate_ids)) == 3
    assert candidates[0].creative_strategy != candidates[1].creative_strategy
    assert candidates[1].creative_strategy != candidates[2].creative_strategy


def test_spoiler_map_generation():
    """Verify StoryUnderstandingAgent generates a detailed spoiler map distinguishing single and combination spoilers."""
    base_dir = Path("sample_data")
    loader = EpisodePackageLoader(base_dir)
    package = loader.load_package()

    story_agent = StoryUnderstandingAgent()
    story_map = story_agent.analyze_story(package)
    spoiler_map = story_agent.generate_spoiler_map(story_map)

    assert isinstance(spoiler_map, SpoilerMap)
    assert spoiler_map.episode_id == package.episode_id
    assert spoiler_map.total_spoilers > 0
    assert len(spoiler_map.single_scene_spoilers) >= 1
    assert len(spoiler_map.combination_spoilers) >= 1

    # Verify combination spoilers have combinations listed
    combo = spoiler_map.combination_spoilers[0]
    assert combo.spoiler_type == "COMBINATION"
    assert len(combo.affected_scenes) > 0 or len(combo.revealed_by_combination_of) > 0


def test_human_approval_escalation_on_unresolvable_failure():
    """Verify that when a failure cannot be resolved automatically, human_approval_required is set with type and reason."""
    base_dir = Path("sample_data")
    loader = EpisodePackageLoader(base_dir)
    package = loader.load_package()

    story_agent = StoryUnderstandingAgent()
    story_map = story_agent.analyze_story(package)

    constraint_agent = ConstraintAnalysisAgent()
    constraint_map = constraint_agent.analyze_constraints(package, reference_date="2026-02-15")

    # Construct an unresolvable plan that points to non-existent scene_99 with zero alternative scenes available
    unresolvable_plan = TrailerPlan(
        trailer_id="unresolvable_v1",
        audience="family",
        duration_seconds=15.0,
        audience_promise="Impossible trailer",
        creative_strategy="Impossible",
        intended_emotional_journey=["none"],
        segments=[
            TrailerSegment(
                segment_id="seg_impossible",
                source_in="00:00:10.000",
                source_out="00:00:25.000",
                scene_id="scene_99_phantom",
                video="scene_99_phantom",
                audio="music_01",
                reason="Unresolvable scene",
                evidence=[]
            )
        ],
        validation=TrailerValidationReport(
            status=ValidationStatus.FAIL,
            items=[
                ValidationResultItem(
                    validator="rights_validator",
                    status=ValidationStatus.FAIL,
                    severity=Severity.HIGH,
                    message="Legal breach: rights expired for underlying format.",
                    evidence=[],
                    affected_segments=["seg_impossible"],
                    suggested_action=RepairAction.ESCALATE_TO_HUMAN
                )
            ],
            summary="Pre-validation failure"
        ),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    # Empty all scenes from package so repair agent cannot substitute any scene
    modified_package = package.model_copy(deep=True)
    modified_package.scenes = []

    repair_agent = RepairAgent()
    repaired_plan, passed = repair_agent.attempt_repair(
        unresolvable_plan, modified_package, story_map, constraint_map, max_attempts=1
    )

    assert passed is False
    assert repaired_plan.human_approval_required is True
    assert repaired_plan.approval_type is not None
    assert repaired_plan.approval_reason is not None
    assert len(repaired_plan.human_approval_requirements) > 0


def test_live_llm_provider_schema_validation():
    """Verify LiveLLMProvider schema validation with mock fallback response."""
    provider = LiveLLMProvider()
    response_str = provider.generate("Plan trailer for family audience")
    import json
    data = json.loads(response_str)
    assert "trailer_id" in data
    assert "segments" in data
    assert isinstance(data["segments"], list)
