"""Test 6: Verification of bias detection and prevention of stereotype-driven personalization."""
from pathlib import Path
from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import ValidationStatus
from src.validators.bias_validator import BiasValidator
from src.models.schemas import TrailerPlan, TrailerSegment, TrailerValidationReport


def test_bias_validator_rejects_spurious_violence_in_dialect_trailer():
    base_dir = Path("sample_data")
    workflow = TrailerDirectorWorkflow(base_dir=base_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)

    # Dialect trailer includes violent night sabotage based on unverified correlation
    plan = TrailerPlan(
        trailer_id="test_dialect_bias_plan",
        audience="dialect_region",
        duration_seconds=15.0,
        audience_promise="Action for rural audience",
        creative_strategy="Followed spurious marketing hypothesis that dialect audience prefers physical violence",
        segments=[
            TrailerSegment(
                segment_id="seg_biased_01",
                source_in="00:15:20.000",
                source_out="00:15:35.000",
                scene_id="scene_08",  # Violent sabotage
                video="scene_08",
                audio="violence",
                reason="Marketing data claimed dialect viewers love violence",
                evidence=["historical_performance:clip_biased_data_claim"]
            )
        ],
        validation=TrailerValidationReport(status=ValidationStatus.PASS, items=[], summary=""),
        estimated_cost=0.05,
        fallback_plan="None"
    )

    validator = BiasValidator()
    results = validator.validate(plan, pkg, story_map, constraint_map)
    failures = [r for r in results if r.status == ValidationStatus.FAIL]
    assert len(failures) > 0, "BiasValidator must reject stereotyping correlations in dialect trailer"
    assert "Bias detected" in failures[0].message
