"""Validator Orchestrator Agent for managing independent verification suites."""
from typing import List, Optional
from src.models.schemas import (
    TrailerPlan,
    TrailerValidationReport,
    ValidationResultItem,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
)
from src.models.enums import ValidationStatus
from src.validators import (
    BaseValidator,
    SourceValidator,
    SpoilerValidator,
    StoryTruthValidator,
    RightsValidator,
    RatingValidator,
    CulturalValidator,
    BiasValidator,
    AccessibilityValidator,
    BudgetValidator,
)
from src.utils.logger import logger, DecisionLogger


class IndependentValidationAgent:
    """Orchestrates independent, deterministic verification across all nine validation layers."""

    def __init__(
        self,
        reference_date: Optional[str] = "2026-04-15",
        decision_logger: Optional[DecisionLogger] = None
    ):
        self.decision_logger = decision_logger
        self.validators: List[BaseValidator] = [
            SourceValidator(),
            SpoilerValidator(),
            StoryTruthValidator(),
            RightsValidator(reference_date=reference_date),
            RatingValidator(),
            CulturalValidator(),
            BiasValidator(),
            AccessibilityValidator(),
            BudgetValidator(),
        ]

    def validate_plan(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> TrailerValidationReport:
        logger.info(f"[IndependentValidationAgent] Running 9 independent validators on trailer '{plan.trailer_id}'")

        all_items: List[ValidationResultItem] = []
        overall_status = ValidationStatus.PASS

        for validator in self.validators:
            results = validator.validate(plan, package, story_map, constraint_map)
            for item in results:
                all_items.append(item)
                if item.status == ValidationStatus.FAIL:
                    overall_status = ValidationStatus.FAIL
                elif item.status == ValidationStatus.PASS_WITH_WARNINGS and overall_status != ValidationStatus.FAIL:
                    overall_status = ValidationStatus.PASS_WITH_WARNINGS

        # Generate summary
        failures = [i for i in all_items if i.status == ValidationStatus.FAIL]
        warnings = [i for i in all_items if i.status == ValidationStatus.PASS_WITH_WARNINGS]
        
        if overall_status == ValidationStatus.FAIL:
            summary = f"VALIDATION FAILED: {len(failures)} critical violations detected across {len(plan.segments)} segments."
        elif overall_status == ValidationStatus.PASS_WITH_WARNINGS:
            summary = f"VALIDATION PASSED WITH WARNINGS: {len(warnings)} non-critical warnings noted."
        else:
            summary = "VALIDATION PASSED: All 9 independent validators verified compliance with rights, rating, truth, and safety."

        report = TrailerValidationReport(
            status=overall_status,
            items=all_items,
            summary=summary
        )
        plan.validation = report

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="IndependentValidationAgent",
                action="VALIDATE_TRAILER",
                reason=summary,
                input_evidence=[f"trailer:{plan.trailer_id}", f"segments:{len(plan.segments)}"],
                selected_decision={"status": overall_status.value, "failures": len(failures), "warnings": len(warnings)},
                validation_results=[item.model_dump() for item in all_items],
                risk="HIGH" if overall_status == ValidationStatus.FAIL else ("MEDIUM" if overall_status == ValidationStatus.PASS_WITH_WARNINGS else "LOW"),
                cost=0.045
            )

        return report
