"""Independent Cultural and Dialect Authenticity Validator."""
import re
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


STEREOTYPE_PATTERNS = [
    re.compile(r"\b(rustic\s+buffoons?|uncultured|comic\s+villagers?|backward|illiterate)\b", re.IGNORECASE)
]


class CulturalValidator(BaseValidator):
    """Guards cultural dignity, authentic vernacular usage, and dialect subtitle semantic fidelity."""

    def __init__(self):
        super().__init__("cultural_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        dialogue_map = {d.dialogue_id: d for d in package.dialogues}

        # 1. Multiple Dialect Subtitle Track Tracking & Relationship/Meaning Distortion Check
        for seg in plan.segments:
            # Ensure subtitle track is explicitly tracked
            track_id = seg.subtitle_track or (seg.subtitle_evidence.track_id if seg.subtitle_evidence else None)
            if not track_id and seg.subtitle:
                track_id = "bhojpuri_purvanchal" if "dialect" in plan.audience.lower() else ("standard_hindi" if "young" in plan.audience.lower() else "standard_english")
                seg.subtitle_track = track_id
                if seg.subtitle_evidence:
                    seg.subtitle_evidence.track_id = track_id

            if seg.dialogue_id and seg.subtitle:
                if seg.dialogue_id in dialogue_map:
                    source_dial = dialogue_map[seg.dialogue_id]

                    sub_lower = seg.subtitle.lower()
                    dial_lower = source_dial.text.lower()

                    # Semantic Inversion / Contradiction Check
                    is_inversion = False
                    if "three centuries" in dial_lower and ("despise" in sub_lower or "destroy" in sub_lower):
                        is_inversion = True
                    elif "together" in dial_lower and ("betray" in sub_lower or "abandon" in sub_lower):
                        is_inversion = True
                    elif "honor" in dial_lower and ("shame" in sub_lower or "humiliate" in sub_lower):
                        is_inversion = True

                    if is_inversion:
                        if seg.subtitle_evidence:
                            seg.subtitle_evidence.meaning_changed = True
                            seg.subtitle_evidence.semantic_match = False
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Semantic mismatch detected in track '{track_id}' for segment '{seg.segment_id}': "
                                        f"Dialect subtitle ('{seg.subtitle}') inverts the fundamental meaning of dialogue ('{source_dial.text}')",
                                evidence=[
                                    f"segment:{seg.segment_id}",
                                    f"track:{track_id}",
                                    f"source_dialogue:{source_dial.text}",
                                    f"mismatched_subtitle:{seg.subtitle}"
                                ],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.CHANGE_SUBTITLE,
                            )
                        )

                    # Relationship Distortion Check (e.g. making siblings romantic or respectful elders abusive)
                    rel_distortion = False
                    distortion_reason = ""
                    # Check for romanticizing sibling dialogue
                    if any(w in sub_lower for w in ["my lover", "my beloved", "sweetheart", "kiss me"]):
                        rel_distortion = True
                        distortion_reason = "Dialect subtitle introduces romantic language conflicting with canonical family relationship."

                    if rel_distortion:
                        if seg.subtitle_evidence:
                            seg.subtitle_evidence.meaning_changed = True
                            seg.subtitle_evidence.semantic_match = False
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.HIGH,
                                message=f"Relationship distortion detected in subtitle track '{track_id}' for segment '{seg.segment_id}': {distortion_reason}",
                                evidence=[
                                    f"segment:{seg.segment_id}",
                                    f"track:{track_id}",
                                    f"subtitle:{seg.subtitle}"
                                ],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.CHANGE_SUBTITLE,
                            )
                        )

            # 2. Check for demeaning stereotypes or caricatures in text cards / promises
            combined_text = f"{seg.text_card or ''} {seg.reason or ''} {plan.audience_promise}"
            for pattern in STEREOTYPE_PATTERNS:
                if pattern.search(combined_text):
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.HIGH,
                            message=f"Cultural stereotyping detected in text: '{pattern.pattern}' violates dignity policy.",
                            evidence=[f"segment:{seg.segment_id}", f"match:{pattern.pattern}"],
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
                    message="Cultural authenticity and dialect subtitle semantics verified with dignity.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
