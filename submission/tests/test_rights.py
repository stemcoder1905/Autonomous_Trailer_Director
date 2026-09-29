"""Test 3: Verification of legal rights, actor promotional riders, and music sync licenses."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.rights_validator import RightsValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport


def test_actor_promotional_embargo_rejected():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Actor Sunil Pandit (Harish) has a strict promotional rider embargo
    plan = TrailerPlan(
        trailer_id="test_rights_actor_plan",
        audience="young_adult",
        duration_seconds=15.0,
        audience_promise="Action",
        creative_strategy="Uses secret guest star",
        segments=[
            TrailerSegment(
                segment_id="seg_rights_01",
                source_in="00:19:30.000",
                source_out="00:19:45.000",
                scene_id="scene_10",
                video="scene_10",
                audio="dialogue",
                dialogue="Harish appears on camera",
                reason="Dramatic guest appearance",
                evidence=["scene:scene_10"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = RightsValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "RightsValidator must reject actor rider embargo violations"
    assert any("actor rider" in f.message.lower() or "embargo" in f.message.lower() for f in failures)


def test_expired_music_license_rejected():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # music_03_synth_pulse expires on 2026-03-31; evaluation date is 2026-04-15
    plan = TrailerPlan(
        trailer_id="test_rights_music_plan",
        audience="young_adult",
        duration_seconds=15.0,
        audience_promise="Action",
        creative_strategy="Uses expired music",
        segments=[
            TrailerSegment(
                segment_id="seg_music_01",
                source_in="00:02:10.000",
                source_out="00:02:18.000",
                scene_id="scene_02",
                video="scene_02",
                audio="synth_track",
                music="music_03_synth_pulse",
                reason="Fast pace",
                evidence=["music:music_03_synth_pulse"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    # Evaluate at date past expiry: 2026-04-15
    validator = RightsValidator(reference_date="2026-04-15")
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "RightsValidator must reject expired music licenses"
    assert any("EXPIRED" in f.message for f in failures)
