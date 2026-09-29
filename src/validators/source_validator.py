"""Source accuracy and grounding validator."""
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
from src.utils.timecode import (
    timecode_to_seconds,
    is_valid_segment_span,
    is_within_bounds,
)


class SourceValidator(BaseValidator):
    """Enforces absolute grounding: scene existence, timecode bounds, dialogue, and asset existence."""

    def __init__(self):
        super().__init__("source_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        scene_map = {s.scene_id: s for s in package.scenes}
        dialogue_map = {d.dialogue_id: d for d in package.dialogues}
        subtitle_map = {sub.subtitle_id: sub for sub in package.subtitles}
        ep_duration = timecode_to_seconds(package.duration_timecode)

        for seg in plan.segments:
            # 1. Scene existence check
            if seg.scene_id not in scene_map:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message=f"Segment '{seg.segment_id}' references non-existent scene '{seg.scene_id}'. "
                                f"Allowed scenes: {list(scene_map.keys())}",
                        evidence=[f"segment:{seg.segment_id}", f"invalid_scene:{seg.scene_id}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.REPLACE_SEGMENT,
                    )
                )
                continue

            scene = scene_map[seg.scene_id]

            # 2. Timecode span validity (source_in < source_out)
            valid_span, span_err = is_valid_segment_span(seg.source_in, seg.source_out)
            if not valid_span:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Segment '{seg.segment_id}' has invalid timecode span: {span_err}",
                        evidence=[f"segment:{seg.segment_id}", f"in:{seg.source_in}", f"out:{seg.source_out}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.ADJUST_TIMECODE,
                    )
                )

            # 3. Within scene bounds check
            within_bounds, bounds_err = is_within_bounds(
                seg.source_in, seg.source_out, scene.start_time, scene.end_time
            )
            if not within_bounds:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Segment '{seg.segment_id}' exceeds scene '{seg.scene_id}' bounds: {bounds_err}",
                        evidence=[
                            f"segment:{seg.segment_id}",
                            f"span:{seg.source_in}-{seg.source_out}",
                            f"scene_bounds:{scene.start_time}-{scene.end_time}"
                        ],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.ADJUST_TIMECODE,
                    )
                )

            # 4. Total media duration check
            out_sec = timecode_to_seconds(seg.source_out)
            if out_sec > ep_duration:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.CRITICAL,
                        message=f"Segment '{seg.segment_id}' source_out ({seg.source_out}) exceeds total episode media duration ({package.duration_timecode})",
                        evidence=[f"segment:{seg.segment_id}", f"ep_duration:{package.duration_timecode}"],
                        affected_segments=[seg.segment_id],
                        suggested_action=RepairAction.ADJUST_TIMECODE,
                    )
                )

            # 5. Dialogue reference verification
            if seg.dialogue_id:
                if seg.dialogue_id not in dialogue_map:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.HIGH,
                            message=f"Segment '{seg.segment_id}' references non-existent dialogue ID '{seg.dialogue_id}'",
                            evidence=[f"dialogue:{seg.dialogue_id}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.REMOVE_DIALOGUE,
                        )
                    )

            # 6. Subtitle reference verification
            if seg.subtitle_id:
                if seg.subtitle_id not in subtitle_map:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.MEDIUM,
                            message=f"Segment '{seg.segment_id}' references non-existent subtitle ID '{seg.subtitle_id}'",
                            evidence=[f"subtitle:{seg.subtitle_id}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.CHANGE_SUBTITLE,
                        )
                    )

        if not results:
            results.append(
                ValidationResultItem(
                    validator=self.name,
                    status=ValidationStatus.PASS,
                    severity=Severity.LOW,
                    message="All segments, timecodes, dialogue, and assets verified against episode source.",
                    evidence=[f"verified_segments:{len(plan.segments)}"],
                    affected_segments=[]
                )
            )

        return results
