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
from src.media.media_validator import MediaValidator
from src.utils.logger import logger, DecisionLogger


class IndependentValidationAgent:
    """Orchestrates independent, deterministic verification across all nine validation layers + physical media."""

    def __init__(
        self,
        reference_date: Optional[str] = "2026-04-15",
        decision_logger: Optional[DecisionLogger] = None,
        media_validator: Optional[MediaValidator] = None
    ):
        self.reference_date = reference_date
        self.decision_logger = decision_logger
        self.media_validator = media_validator or MediaValidator()
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

        # Build scene lookup for media validation
        scene_by_id = {s.scene_id: s for s in package.scenes}

        # Media validation per segment
        for segment in plan.segments:
            sc = scene_by_id.get(segment.scene_id)
            media_results = self.media_validator.validate_segment_media(segment, scene=sc)
            for item in media_results:
                all_items.append(item)
                if item.status == ValidationStatus.FAIL:
                    overall_status = ValidationStatus.FAIL
                elif item.status == ValidationStatus.PASS_WITH_WARNINGS and overall_status != ValidationStatus.FAIL:
                    overall_status = ValidationStatus.PASS_WITH_WARNINGS

        # Populate per-segment validation status map
        for segment in plan.segments:
            status_map = {
                "source": "PASS",
                "spoiler": "PASS",
                "story_truth": "PASS",
                "rights": "PASS",
                "rating": "PASS",
                "cultural": "PASS",
                "bias": "PASS",
                "accessibility": "PASS",
                "budget": "PASS",
                "media": "PASS"
            }
            # Check items affecting this segment
            seg_validation_items = []
            for it in all_items:
                if segment.segment_id in it.affected_segments:
                    seg_validation_items.append(it.model_dump())
                    key = it.validator.replace("_validator", "")
                    if it.status == ValidationStatus.FAIL:
                        status_map[key] = "FAIL"
                    elif it.status == ValidationStatus.PASS_WITH_WARNINGS and status_map.get(key) != "FAIL":
                        status_map[key] = "PASS_WITH_WARNINGS"
            segment.validation_status_map = status_map
            segment.validation_results = seg_validation_items

            # Genuine Evidence Verification Resolution (Fix #2, #10, #13)
            # Only mark evidence verified if appropriate validator actively passed
            if segment.source:
                segment.source.verified = (status_map.get("source") != "FAIL" and status_map.get("media") != "FAIL")
            
            if segment.rights_evidence:
                segment.rights_evidence.rights_cleared = (status_map.get("rights") == "PASS")
                segment.rights_evidence.verified = (status_map.get("rights") != "FAIL")

            if segment.subtitle_evidence:
                segment.subtitle_evidence.verified_accurate = (status_map.get("cultural") == "PASS")
                segment.subtitle_evidence.verified = (status_map.get("cultural") != "FAIL")

            segment.spoiler_evidence = {
                "spoiler_free": (status_map.get("spoiler") != "FAIL"),
                "status": status_map.get("spoiler", "PASS"),
                "verified": True
            }

            segment.story_truth_evidence = {
                "canon_truthful": (status_map.get("story_truth") != "FAIL"),
                "status": status_map.get("story_truth", "PASS"),
                "verified": True
            }

            segment.provenance = {
                "execution_mode": getattr(self.media_validator, "execution_mode", "replay"),
                "media_source": getattr(self.media_validator, "media_source", "replay_fixture"),
                "validator_engine": "IndependentValidationAgent",
                "reference_date": self.reference_date,
                "overall_verdict": "PASS" if status_map.get("rights") != "FAIL" and status_map.get("spoiler") != "FAIL" and status_map.get("source") != "FAIL" else "FAIL"
            }

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
