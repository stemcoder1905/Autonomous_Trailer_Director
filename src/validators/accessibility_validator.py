"""Independent Accessibility Validator."""
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
from src.utils.timecode import timecode_to_seconds


class AccessibilityValidator(BaseValidator):
    """Enforces subtitling presence, reading speed (CPS), display duration, and multimodal readability."""

    def __init__(self):
        super().__init__("accessibility_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        policy = constraint_map.accessibility_requirements.get("subtitles", {})
        max_cps = policy.get("max_reading_speed_cps", 21.0)
        min_duration = policy.get("min_display_duration_seconds", 1.2)

        for seg in plan.segments:
            seg_duration = timecode_to_seconds(seg.source_out) - timecode_to_seconds(seg.source_in)

            # 1. Dialogue must have accompanying subtitle
            if seg.dialogue and not seg.subtitle:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Segment '{seg.segment_id}' contains spoken dialogue without required accessible subtitles.",
                        evidence=[f"segment:{seg.segment_id}", f"dialogue:{seg.dialogue}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.CHANGE_SUBTITLE,
                    )
                )

            # 2. Reading speed CPS check
            if seg.subtitle and seg_duration > 0:
                char_count = len(seg.subtitle)
                cps = char_count / seg_duration
                if cps > max_cps:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.MEDIUM,
                            message=f"Segment '{seg.segment_id}' subtitle reading speed ({cps:.1f} CPS) "
                                    f"exceeds accessibility threshold of {max_cps} CPS (length: {char_count} chars in {seg_duration:.1f}s)",
                            evidence=[f"segment:{seg.segment_id}", f"cps:{cps:.1f}", f"max_cps:{max_cps}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.ADJUST_TIMECODE,
                        )
                    )

            # 3. Minimum display duration
            if (seg.subtitle or seg.dialogue) and seg_duration < min_duration:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.MEDIUM,
                        message=f"Segment '{seg.segment_id}' duration ({seg_duration:.2f}s) is shorter than minimum readable threshold ({min_duration}s)",
                        evidence=[f"segment:{seg.segment_id}", f"duration:{seg_duration:.2f}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.ADJUST_TIMECODE,
                    )
                )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message="Full accessibility compliance: verified subtitle presence, CPS thresholds, and timing.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
