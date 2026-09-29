"""Test 11: Verification that marketing clickbait and false canonical relationships are rejected."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.story_truth_validator import StoryTruthValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport
from src.agents.repair_agent import RepairAgent


def test_clickbait_false_romance_rejected_and_repaired():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Marketing requested clickbait framing Dev and Meera (canonical siblings) as romantic lovers
    plan = TrailerPlan(
        trailer_id="test_clickbait_plan",
        audience="young_adult",
        duration_seconds=15.0,
        audience_promise="A forbidden romance between Dev and Meera",
        creative_strategy="Manufacture romantic passion between brother and sister",
        segments=[
            TrailerSegment(
                segment_id="seg_clickbait_01",
                source_in="00:04:15.000",
                source_out="00:04:25.000",
                scene_id="scene_03",
                video="scene_03",
                audio="romantic_music",
                text_card="A FORBIDDEN LOVE: DEV & MEERA",
                reason="Marketing requested sensational romantic hook",
                evidence=["scene:scene_03"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = StoryTruthValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "StoryTruthValidator must reject manufactured false romance between siblings"
    assert "Manufactured false romance" in failures[0].message

    # Test automatic repair
    repair_agent = RepairAgent()
    repaired_plan, success = repair_agent.attempt_repair(plan, pkg, story_map, constraint_map)
    assert success is True
    assert "romance" not in repaired_plan.segments[0].text_card.lower()
    assert "family" in repaired_plan.segments[0].text_card.lower() or "sibling" in repaired_plan.creative_strategy.lower()
