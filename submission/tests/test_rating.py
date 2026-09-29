"""Test 4: Verification of rating policies and audience safety thresholds."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.rating_validator import RatingValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport


def test_family_rating_policy_enforced():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Scene 08 is rated PG-13 due to physical sabotage and darkness
    plan = TrailerPlan(
        trailer_id="test_family_rating_plan",
        audience="family",
        duration_seconds=15.0,
        audience_promise="Family warmth",
        creative_strategy="Accidentally incorporates night peril",
        segments=[
            TrailerSegment(
                segment_id="seg_rating_01",
                source_in="00:15:20.000",
                source_out="00:15:35.000",
                scene_id="scene_08",  # PG-13 and prohibited for family
                video="scene_08",
                audio="action",
                reason="Dramatic suspense",
                evidence=["scene:scene_08"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = RatingValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "RatingValidator must reject PG-13 / prohibited scenes from family trailers"
    assert any("prohibited for audience" in f.message or "PG-13" in f.message for f in failures)
