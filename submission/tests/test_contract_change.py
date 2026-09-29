"""Test 5: Verification of change impact analysis and selective replanning."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ConstraintStatus, ValidationStatus
from src.models.schemas import ConstraintRule


def test_selective_replanning_on_contract_change():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    
    # 1. Run baseline workflow - generates all 3 plans
    state = workflow.run()
    assert len(state.trailer_plans) == 3
    assert state.trailer_plans["family"].validation.status != ValidationStatus.FAIL
    assert state.trailer_plans["young_adult"].validation.status != ValidationStatus.FAIL
    assert state.trailer_plans["dialect_region"].validation.status != ValidationStatus.FAIL

    # Record snapshot of original family and dialect segments
    family_segs_before = [s.model_dump() for s in state.trailer_plans["family"].segments]
    dialect_segs_before = [s.model_dump() for s in state.trailer_plans["dialect_region"].segments]

    # 2. Trigger contract expiration for music_03_synth_pulse (used ONLY in young_adult)
    expired_rule = ConstraintRule(
        rule_id="rule_contract_music_03",
        type="music_restriction",
        scope="asset:music_03_synth_pulse",
        condition="music == 'music_03_synth_pulse'",
        allowed_behavior="None",
        blocked_behavior="License expired on 2026-03-31; all promotional sync prohibited.",
        evidence=["Contract Amendment Notice MUS-2026-03-EXP"],
        status=ConstraintStatus.EXPIRED,
        effective_date="2026-01-01",
        expiry_date="2026-03-31"
    )

    state = workflow.trigger_contract_modification(state, expired_rule)

    assert len(state.change_impact_reports) == 1
    report = state.change_impact_reports[0]

    # Assert Young Adult trailer was affected and replanned
    assert "young_adult_v1" in report.affected_trailers
    assert len(report.affected_segments["young_adult_v1"]) > 0

    # Assert Family and Dialect trailers were NOT affected
    assert "family_v1" in report.unaffected_trailers
    assert "dialect_region_v1" in report.unaffected_trailers

    # Assert Family and Dialect segments were preserved completely intact
    family_segs_after = [s.model_dump() for s in state.trailer_plans["family"].segments]
    dialect_segs_after = [s.model_dump() for s in state.trailer_plans["dialect_region"].segments]
    assert family_segs_before == family_segs_after
    assert dialect_segs_before == dialect_segs_after

    # Assert Young Adult segments now use safe replacement music
    for seg in state.trailer_plans["young_adult"].segments:
        assert seg.music != "music_03_synth_pulse"
        assert seg.music == "music_01_folk_acoustic"
    
    # Assert new validation status for young adult is valid
    assert state.trailer_plans["young_adult"].validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
