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

        # 1. Check total estimated plan cost
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

        # 2. Check actual provider cost spend if tracked
        if plan.actual_cost is not None and plan.actual_cost > limit_usd:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.FAIL,
                    severity=Severity.CRITICAL,
                    message=f"Actual provider spend (${plan.actual_cost:.2f} USD) exceeded budget threshold of ${limit_usd:.2f} USD.",
                    evidence=[f"actual_cost:{plan.actual_cost}", f"limit:{limit_usd}"],
                    affected_segments=[],
                    suggested_action=RepairAction.REPLACE_SEGMENT,
                )
            )

        # 3. Enforce Configurable Resource Call Quotas (LLM, Vision, ASR, Media)
        cost_sheet = package.cost_sheet if hasattr(package, "cost_sheet") else None
        max_llm_calls = cost_sheet.max_llm_calls if cost_sheet else 50
        max_vision_calls = cost_sheet.max_vision_calls if cost_sheet else 20
        max_asr_calls = 30

        usage = plan.resource_usage or {}
        llm_calls = usage.get("llm_calls", 0)
        vision_calls = usage.get("vision_calls", 0)
        asr_calls = usage.get("asr_calls", 0)

        if llm_calls > max_llm_calls:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Resource quota exceeded: LLM calls ({llm_calls}) exceeded ceiling of {max_llm_calls}.",
                    evidence=[f"llm_calls:{llm_calls}", f"max:{max_llm_calls}"],
                    affected_segments=[],
                    suggested_action=RepairAction.REPLACE_SEGMENT
                )
            )

        if vision_calls > max_vision_calls:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Resource quota exceeded: Vision frame calls ({vision_calls}) exceeded ceiling of {max_vision_calls}.",
                    evidence=[f"vision_calls:{vision_calls}", f"max:{max_vision_calls}"],
                    affected_segments=[],
                    suggested_action=RepairAction.REPLACE_SEGMENT
                )
            )

        if asr_calls > max_asr_calls:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.FAIL,
                    severity=Severity.HIGH,
                    message=f"Resource quota exceeded: ASR calls ({asr_calls}) exceeded ceiling of {max_asr_calls}.",
                    evidence=[f"asr_calls:{asr_calls}", f"max:{max_asr_calls}"],
                    affected_segments=[],
                    suggested_action=RepairAction.REPLACE_SEGMENT
                )
            )

        # 4. Explicit cost accounting: populate actual_cost separate from estimated_cost
        if plan.actual_cost is None:
            # Replay mode has actual provider spend of 0.00
            plan.actual_cost = 0.00
            plan.cost_breakdown = {
                "llm_actual_usd": 0.00,
                "vision_actual_usd": 0.00,
                "asr_actual_usd": 0.00,
                "media_processing_actual_usd": 0.00,
                "estimated_plan_usd": plan.estimated_cost
            }

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message=f"Budget compliance verified: estimated cost (${plan.estimated_cost:.2f} USD), actual cost (${plan.actual_cost:.2f} USD) within ${limit_usd:.2f} limit. Resource calls within quotas.",
                    evidence=[f"estimated_cost:{plan.estimated_cost}", f"actual_cost:{plan.actual_cost}", f"llm_calls:{llm_calls}"],
                    affected_segments=[]
                )
            )

        return results
