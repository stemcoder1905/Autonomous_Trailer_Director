"""Test 7: Verification of dialect subtitle semantic fidelity and mismatch detection."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.cultural_validator import CulturalValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport
from src.agents.repair_agent import RepairAgent


def test_dialect_subtitle_semantic_mismatch_detected_and_repaired():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Dialect subtitle inverts father's affectionate heritage into hatred
    plan = TrailerPlan(
        trailer_id="test_mismatch_plan",
        audience="dialect_region",
        duration_seconds=15.0,
        audience_promise="Cultural drama",
        creative_strategy="Uses corrupted subtitle track",
        segments=[
            TrailerSegment(
                segment_id="seg_mismatch_01",
                source_in="00:00:15.000",
                source_out="00:00:20.000",
                scene_id="scene_01",
                video="scene_01",
                audio="dialogue",
                dialogue="Our looms have sung this rhythm for three centuries, Dev.",
                dialogue_id="dial_01",
                subtitle="I despise you and will destroy our looms forever.",  # Semantic inversion!
                subtitle_id="sub_corrupted_01",
                reason="Corrupted translation",
                evidence=["scene:scene_01"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = CulturalValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "CulturalValidator must detect severe semantic inversion in dialect subtitle"
    assert "Semantic mismatch detected" in failures[0].message

    # Test automatic repair of semantic mismatch
    repair_agent = RepairAgent()
    repaired_plan, success = repair_agent.attempt_repair(plan, pkg, story_map, constraint_map)
    assert success is True
    # Subtitle must now match the canonical dialogue
    assert "three centuries" in repaired_plan.segments[0].subtitle.lower()
