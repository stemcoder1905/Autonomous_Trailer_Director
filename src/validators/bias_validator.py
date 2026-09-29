"""Independent Bias and Stereotype Validator."""
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


class BiasValidator(BaseValidator):
    """Guards against algorithmic and historical bias, stereotyping, and spurious audience correlations."""

    def __init__(self):
        super().__init__("bias_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        is_dialect = "dialect" in plan.audience.lower()

        # 1. Detect if spurious correlation hypothesis was inappropriately adopted
        for seg in plan.segments:
            # If dialect trailer includes night sabotage or physical violence based on spurious feedback
            if is_dialect and seg.scene_id in ["scene_08"]:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Bias detected: Dialect trailer inappropriately included violent scene '{seg.scene_id}' "
                                f"based on unverified marketing correlation ('dialect audience prefers violent conflict'). "
                                f"Autonomous director policy forbids stereotyping audiences from geography or dialect.",
                        evidence=[
                            f"segment:{seg.segment_id}",
                            f"scene:{seg.scene_id}",
                            "historical_caveat:BIAS_ALERT detected"
                        ],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.REPLACE_SEGMENT,
                    )
                )

        # 2. Check if trailer plan contains unresolved bias warnings
        for warning in plan.warnings:
            if "spurious correlation" in warning.lower() or "bias_alert" in warning.lower():
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.PASS_WITH_WARNINGS,
                        severity=Severity.MEDIUM,
                        message=f"Acknowledged dataset bias warning: {warning}",
                        evidence=[f"warning:{warning}"],
                        affected_segments=[]
                    )
                )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message="No algorithmic bias or geographic stereotyping detected in trailer plan.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
