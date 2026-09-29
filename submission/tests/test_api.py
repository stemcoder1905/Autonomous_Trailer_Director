"""Test 12: Verification of FastAPI web endpoints."""
from src.api import health_check, analyze_episode, run_workflow, RunRequest


def test_api_health():
    res = health_check()
    assert res["status"] == "healthy"
    assert "version" in res


def test_api_analyze():
    req = RunRequest(input_path="sample_data")
    res = analyze_episode(req)
    assert "story_map" in res
    assert "constraint_map" in res
    assert len(res["story_map"]["events"]) > 0


def test_api_run():
    req = RunRequest(input_path="sample_data", audience="family")
    res = run_workflow(req)
    assert res["status"] == "success"
    assert "family" in res["plans"]
    assert len(res["plans"]["family"]["segments"]) > 0
