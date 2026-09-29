"""Independent Budget and Resource Guardrail Validator."""
from typing import List
from src.validators.base import BaseValidator
from src.models.schemas import (
    TrailerPlan,
    ValidationResultItem,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
)
from src.models.enums import ValidationStatus, Severity, RepairAction


class BudgetValidator(BaseValidator):
    """Enforces computational budget limits and cost ceilings."""

    def __init__(self):
        super().__init__("budget_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        limit_usd = constraint_map.budget_limit_usd

        # Check total estimated plan cost
        if plan.estimated_cost > limit_usd:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Trailer plan estimated cost (${plan.estimated_cost:.2f} USD) exceeds budget threshold of ${limit_usd:.2f} USD.",
                    evidence=[f"estimated_cost:{plan.estimated_cost}", f"limit:{limit_usd}"],
                    affected_segments=[],
                    suggested_action=RepairAction.REPLACE_SEGMENT,
                )
            )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message=f"Budget compliance verified: estimated cost (${plan.estimated_cost:.2f} USD) within ${limit_usd:.2f} limit.",
                    evidence=[f"cost:{plan.estimated_cost}"],
                    affected_segments=[]
                )
            )

        return results
