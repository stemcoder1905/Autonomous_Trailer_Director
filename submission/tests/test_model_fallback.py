"""Test 9: Verification of model provider abstraction and automated fallback resilience."""
from src.providers.llm import ProviderManager, PrimaryLLMProvider, FallbackLLMProvider
from src.providers.mock import MockLLMProvider


def test_provider_fallback_to_mock_on_primary_failure():
    # Simulate primary failure
    mgr = ProviderManager(preferred_provider="primary", simulate_primary_failure=True)
    active = mgr.get_active_provider()
    
    assert isinstance(active, MockLLMProvider)
    assert mgr.active_provider_name == "mock"

    # Test successful completion generation through fallback
    prompt = "plan trailer for family"
    completion = mgr.generate(prompt)
    assert len(completion) > 0
    assert "family" in completion.lower()
    assert mgr.total_calls >= 1


def test_unconfigured_primary_provider_reports_unhealthy():
    provider = PrimaryLLMProvider(api_key="")
    assert provider.is_healthy() is False


def test_provider_manager_fallback_provenance():
    mgr = ProviderManager(preferred_provider="live", simulate_primary_failure=True)
    mgr.generate("Create narrative trailer plan")
    prov = mgr.get_provenance()
    assert prov["fallback_used"] is True
    assert prov["source_type"] == "MOCK_MODEL"
    assert "Simulated primary failure" in prov["fallback_reason"]


def test_vision_provider_manager_fallback():
    from src.providers.vision import VisionProviderManager
    from pathlib import Path
    
    v_mgr = VisionProviderManager(preferred_provider="live", simulate_failure=True)
    res = v_mgr.verify_frame(
        frame_path=Path("sample_data/media/frames/scene_01_frame_001.jpg"),
        claim="Dev operates traditional wooden loom",
        scene_id="scene_01"
    )
    assert res is not None
    assert res.status in ["PASS", "FAIL", "REVIEW"]
    prov = v_mgr.last_provenance
    assert prov["fallback_used"] is True
    assert prov["source_type"] == "MOCK_MODEL"
    assert "Simulated" in prov["fallback_reason"]


def test_e2e_model_failure_scenario_execution():
    from pathlib import Path
    from src.workflow.graph import TrailerDirectorWorkflow
    from src.models.enums import ValidationStatus

    workflow = TrailerDirectorWorkflow(
        base_dir=Path("sample_data"),
        reference_date="2026-02-15"
    )
    state = workflow.run(scenario="model_failure")
    assert len(state.trailer_plans) == 3
    for aud, plan in state.trailer_plans.items():
        assert plan.validation.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]
        assert len(plan.segments) > 0
