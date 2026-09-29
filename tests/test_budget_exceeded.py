"""Test 10: Verification of budget limits and cost guardrail validation."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.budget_validator import BudgetValidator
from src.models.schemas import TrailerPlan, TrailerValidationReport


def test_budget_exceeded_fails_validation():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Plan with estimated cost ($45.00 USD) exceeding $25.00 limit
    plan = TrailerPlan(
        trailer_id="test_expensive_plan",
        audience="young_adult",
        duration_seconds=30.0,
        audience_promise="High budget cinematic cut",
        creative_strategy="Excessive multimodal processing",
        segments=[],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=45.00,  # Exceeds 25.00
        fallback_plan="Switch to low-cost deterministic templates"
    )

    validator = BudgetValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "BudgetValidator must reject plans exceeding budget threshold"
    assert "exceeds budget threshold" in failures[0].message
