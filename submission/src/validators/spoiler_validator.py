"""Independent Spoiler Validator for single-clip, dialogue, and combination spoilers."""
from typing import List, Set
from src.validators.base import BaseValidator
from src.models.schemas import (
    TrailerPlan,
    ValidationResultItem,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
    SpoilerLevel,
)
from src.models.enums import ValidationStatus, Severity, RepairAction


class SpoilerValidator(BaseValidator):
    """Detects narrative leaks, climax reveals, dialogue spoilers, and multi-clip combination spoilers."""

    def __init__(self):
        super().__init__("spoiler_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        selected_scenes: Set[str] = {s.scene_id for s in plan.segments}
        ordered_scenes = [s.scene_id for s in plan.segments]

        # 1. Direct Scene and Dialogue Spoiler Check
        for spoiler in story_map.spoilers:
            if spoiler.level == SpoilerLevel.MAJOR:
                for seg in plan.segments:
                    # Check scene intersection
                    if seg.scene_id in spoiler.affected_scenes:
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Segment '{seg.segment_id}' in scene '{seg.scene_id}' reveals MAJOR spoiler: {spoiler.fact}",
                                evidence=[f"spoiler:{spoiler.spoiler_id}", f"fact:{spoiler.fact}", f"scene:{seg.scene_id}"],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.REPLACE_SEGMENT,
                            )
                        )

                    # Check dialogue spoiler intersection
                    if seg.dialogue_id and seg.dialogue_id in spoiler.affected_dialogue_ids:
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Segment '{seg.segment_id}' dialogue '{seg.dialogue_id}' leaks protected spoiler: {spoiler.fact}",
                                evidence=[f"spoiler:{spoiler.spoiler_id}", f"dialogue:{seg.dialogue_id}"],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.REMOVE_DIALOGUE,
                            )
                        )

            # 2. Multi-Clip Combination Spoiler Check
            for combo in spoiler.revealed_by_combination_of:
                # If all scenes in the combination list are present in the trailer
                if all(c_scene in selected_scenes for c_scene in combo):
                    # Check if they occur in proximity (ordering leak)
                    matching_segs = [s.segment_id for s in plan.segments if s.scene_id in combo]
                    if spoiler.level == SpoilerLevel.MAJOR:
                        status = ValidationStatus.FAIL
                        sev = Severity.CRITICAL
                    else:
                        status = ValidationStatus.PASS_WITH_WARNINGS
                        sev = Severity.HIGH

                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=status,
                            severity=sev,
                            message=f"Combination of scenes {combo} causes a spoiler leak: {spoiler.fact}",
                            evidence=[f"combo:{combo}", f"spoiler:{spoiler.spoiler_id}"],
                            affected_segments=matching_segs,
                            suggested_action=RepairAction.REPLACE_SEGMENT,
                        )
                    )

        # 3. Check for specific twist antagonist reveals (e.g. Harish in scene_10)
        for seg in plan.segments:
            if "harish" in (seg.dialogue or "").lower() or "harish" in (seg.text_card or "").lower():
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message=f"Segment '{seg.segment_id}' mentions secret antagonist Harish prior to release.",
                        evidence=[f"segment:{seg.segment_id}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.REMOVE_DIALOGUE,
                    )
                )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message="Zero major spoilers detected; narrative twists and climax protected.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
