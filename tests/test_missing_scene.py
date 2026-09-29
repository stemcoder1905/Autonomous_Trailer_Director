"""Test 1: Verification that hallucinated or non-existent scenes are rejected."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.source_validator import SourceValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport


def test_missing_scene_rejected():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Propose hallucinated scene_25
    plan = TrailerPlan(
        trailer_id="test_missing_scene_plan",
        audience="family",
        duration_seconds=15.0,
        audience_promise="A fake trailer",
        creative_strategy="Uses phantom scene",
        segments=[
            TrailerSegment(
                segment_id="seg_invalid_01",
                source_in="00:01:00.000",
                source_out="00:01:15.000",
                scene_id="scene_25",  # INVALID
                video="scene_25",
                audio="music",
                reason="Hallucinated by LLM",
                evidence=["scene:scene_25"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = SourceValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)

    # Must fail source validation
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "SourceValidator must fail when a non-existent scene is referenced"
    assert "scene_25" in failures[0].message
