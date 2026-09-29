"""Independent Rating and Content Safety Validator."""
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


class RatingValidator(BaseValidator):
    """Enforces audience-specific content ratings and safety policies."""

    def __init__(self):
        super().__init__("rating_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        rating_rules = constraint_map.rating_rules
        audience_key = plan.audience.lower().replace(" ", "_").replace("-", "_").split("_")[0]
        # Normalize keys: "family", "young", "dialect"
        if "family" in audience_key:
            policy = rating_rules.get("family", {})
        elif "young" in audience_key:
            policy = rating_rules.get("young_adult", {})
        elif "dialect" in audience_key:
            policy = rating_rules.get("dialect_region", {})
        else:
            policy = {}

        prohibited_scenes = policy.get("prohibited_scenes", [])
        scene_map = {s.scene_id: s for s in package.scenes}

        for seg in plan.segments:
            if seg.scene_id in scene_map:
                scene = scene_map[seg.scene_id]

                # 1. Prohibited scenes for audience policy
                if seg.scene_id in prohibited_scenes:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.HIGH,
                            message=f"Segment '{seg.segment_id}' uses scene '{seg.scene_id}' which is prohibited for audience '{plan.audience}' due to content rating policy.",
                            evidence=[f"policy:{plan.audience}", f"prohibited_scene:{seg.scene_id}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.REPLACE_SEGMENT,
                        )
                    )

                # 2. Family audience strict checks (No PG-13 or violence flags)
                if "family" in audience_key:
                    if "PG-13" in scene.rating_flags:
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.HIGH,
                                message=f"Family trailer cannot include PG-13 scene '{seg.scene_id}' (rating flags: {scene.rating_flags})",
                                evidence=[f"scene:{seg.scene_id}", f"flags:{scene.rating_flags}"],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.REPLACE_SEGMENT,
                            )
                        )
                    if scene.emotion in ["peril_action", "suspense_thrill", "shocking_betrayal"]:
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.MEDIUM,
                                message=f"Family trailer includes unsuitable emotion '{scene.emotion}' in scene '{seg.scene_id}'",
                                evidence=[f"scene:{seg.scene_id}", f"emotion:{scene.emotion}"],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.REPLACE_SEGMENT,
                            )
                        )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message=f"Content rating fully compliant with {plan.audience} policy standards.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
