"""Test 2: Verification that major plot spoilers and combination spoilers are rejected."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.spoiler_validator import SpoilerValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport


def test_major_spoiler_rejected():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Scene 10 is the major climax twist reveal of Uncle Harish
    plan = TrailerPlan(
        trailer_id="test_spoiler_plan",
        audience="family",
        duration_seconds=15.0,
        audience_promise="Climax reveal",
        creative_strategy="Uses top performing historical scene",
        segments=[
            TrailerSegment(
                segment_id="seg_spoiler_01",
                source_in="00:19:30.000",
                source_out="00:19:45.000",
                scene_id="scene_10",  # MAJOR SPOILER
                video="scene_10",
                audio="dialogue",
                dialogue="You thought Vikram acted alone? It was always my money, nephew.",
                dialogue_id="dial_10",
                reason="High historical engagement",
                evidence=["scene:scene_10"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = SpoilerValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)

    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "SpoilerValidator must reject major spoiler scene_10"
    assert any("MAJOR spoiler" in f.message for f in failures)


def test_combination_spoiler_detected():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Combining scene_08 (sabotage) and scene_09 (instant recovery) leaks resolution
    plan = TrailerPlan(
        trailer_id="test_combo_spoiler_plan",
        audience="young_adult",
        duration_seconds=25.0,
        audience_promise="Tension and fix",
        creative_strategy="Combines catastrophe and immediate fix",
        segments=[
            TrailerSegment(
                segment_id="seg_combo_01",
                source_in="00:15:30.000",
                source_out="00:15:40.000",
                scene_id="scene_08",
                video="scene_08",
                audio="action",
                reason="Sabotage crisis",
                evidence=["scene:scene_08"]
            ),
            TrailerSegment(
                segment_id="seg_combo_02",
                source_in="00:18:00.000",
                source_out="00:18:15.000",
                scene_id="scene_09",
                video="scene_09",
                audio="cheer",
                reason="Instant recovery",
                evidence=["scene:scene_09"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = SpoilerValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    combo_warnings = [r for r in results if "Combination of scenes" in r.message]
    assert len(combo_warnings) > 0, "SpoilerValidator must detect multi-clip combination spoiler"
