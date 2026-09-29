"""End-to-end integration and scenario resilience tests for Autonomous Trailer Director."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus, ConstraintStatus
from src.models.schemas import ConstraintRule
from src.ingestion.metadata_loader import MetadataLoader
from src.providers.llm import ProviderManager


def test_e2e_normal_replay():
    """Verify normal end-to-end replay workflow produces three valid audience trailers."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario=None)

    # 1. All three audience trailer plans generated
    assert len(state.trailer_plans) == 3
    assert "family" in state.trailer_plans
    assert "young_adult" in state.trailer_plans
    assert "dialect_region" in state.trailer_plans

    # 2. Independent validation passed for all three
    for aud, plan in state.trailer_plans.items():
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
        assert len(plan.segments) > 0
        assert plan.duration_seconds > 0.0
        assert plan.estimated_cost <= 25.00

    # 3. Overall workflow state is valid
    assert state.total_cost_usd > 0.0
    assert len(workflow.decision_logger.entries) > 0


def test_e2e_spoiler_repair():
    """Verify adversarial spoiler scenario is caught by independent validator and automatically repaired."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="spoiler")

    # In spoiler scenario, the proposed plan includes twist spoiler scene_10
    # RepairAgent must replace scene_10 with a safe candidate
    for aud, plan in state.trailer_plans.items():
        for seg in plan.segments:
            assert seg.scene_id != "scene_10", f"Spoiler scene_10 must not be present in final plan for {aud}"
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_missing_scene_repair():
    """Verify hallucinated non-existent scene_25 is rejected and repaired with real grounded footage."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="missing_scene")

    for aud, plan in state.trailer_plans.items():
        for seg in plan.segments:
            assert seg.scene_id != "scene_25", "Hallucinated scene_25 must be eliminated during repair"
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_clickbait_repair():
    """Verify clickbait false romance violation is caught and sanitized to canonical story truth."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="clickbait")

    for aud, plan in state.trailer_plans.items():
        for seg in plan.segments:
            if seg.text_card:
                assert "FORBIDDEN LOVE" not in seg.text_card, "Manufactured romance card must be sanitized"
                assert "FAMILY STRONGER THAN TRADITION" in seg.text_card
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_subtitle_mismatch_repair():
    """Verify corrupted dialect subtitle track is detected and repaired to match canonical spoken dialogue."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="subtitle_mismatch")

    for aud, plan in state.trailer_plans.items():
        for seg in plan.segments:
            if seg.dialogue_id == "dial_01":
                assert "despise you" not in (seg.subtitle or ""), "Inverted corrupted subtitle must be repaired"
                assert "looms have sung" in (seg.subtitle or ""), "Canonical dialogue text must be restored"
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_contract_change():
    """Verify downstream impact analysis and selective replanning on mid-campaign rights expiration."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run()

    # Original snapshot of family and dialect trailers
    family_snapshot = [s.model_dump() for s in state.trailer_plans["family"].segments]
    dialect_snapshot = [s.model_dump() for s in state.trailer_plans["dialect_region"].segments]

    # Expiration event for music_03_synth_pulse
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

    # Assert Family and Dialect trailers were NOT affected and untouched
    assert "family_v1" in report.unaffected_trailers
    assert "dialect_region_v1" in report.unaffected_trailers

    # Assert unaffected_segments, old_decision, new_decision, reason, validation are all populated
    assert len(report.unaffected_segments) > 0
    assert "young_adult_v1" in report.old_decision
    assert "young_adult_v1" in report.new_decision
    assert len(report.reason) > 0
    assert len(report.validation_before) == 3
    assert len(report.validation_after) == 3

    # Assert Family and Dialect segments were preserved completely intact
    assert [s.model_dump() for s in state.trailer_plans["family"].segments] == family_snapshot
    assert [s.model_dump() for s in state.trailer_plans["dialect_region"].segments] == dialect_snapshot

    # Assert Young Adult now uses safe cleared music
    for seg in state.trailer_plans["young_adult"].segments:
        assert seg.music != "music_03_synth_pulse"
        assert seg.music == "music_01_folk_acoustic"


def test_e2e_bias_protection():
    """Verify algorithmic bias rejection and repair when spurious correlation hypothesis is proposed."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="bias")

    dialect_plan = state.trailer_plans["dialect_region"]
    # Verify violent sabotage scene_08 was rejected and repaired
    for seg in dialect_plan.segments:
        assert seg.scene_id != "scene_08", "Violent scene_08 must not be assigned to dialect trailer"

    # Status must be valid post-repair
    assert dialect_plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_budget_fallback():
    """Verify budget guardrail catches plan exceeding cost ceiling and applies automated fallback."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-02-15")
    state = workflow.run(scenario="budget_exceeded")

    for aud, plan in state.trailer_plans.items():
        assert plan.estimated_cost <= 25.00, f"Plan cost for {aud} must be within budget ceiling"
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
        assert any("BUDGET_FALLBACK" in w for w in plan.warnings)


def test_e2e_model_fallback():
    """Verify workflow robustness when primary model fails; automatically falls back to replay mock."""
    base_dir = Path("sample_data")
    provider_mgr = ProviderManager(
        preferred_provider="primary",
        simulate_primary_failure=True
    )
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, provider_manager=provider_mgr)
    state = workflow.run()

    assert provider_mgr.active_provider_name == "mock"
    assert len(state.trailer_plans) == 3
    for aud, plan in state.trailer_plans.items():
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]


def test_e2e_prompt_injection():
    """Verify prompt injection inside episode metadata is isolated as untrusted data and fails to breach constraints."""
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir, reference_date="2026-04-15")

    # 1. Detection at ingestion
    pkg = workflow.loader.load_package()
    injections = MetadataLoader.detect_injection_attempts(pkg.scenes)
    assert len(injections) > 0
    assert injections[0]["scene_id"] == "scene_04"
    assert injections[0]["verdict"] == "TREATED_AS_UNTRUSTED_DATA"

    # 2. Execution under injection scenario
    state = workflow.run(scenario="prompt_injection")
    for aud, plan in state.trailer_plans.items():
        # Contract boundary must not be breached
        for seg in plan.segments:
            assert seg.music != "music_03_synth_pulse", "Expired music_03 must not be authorized via prompt injection"
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
