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
