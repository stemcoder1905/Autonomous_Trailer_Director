"""Independent Story Truth Validator for guarding narrative fidelity and canonical relationships."""
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


ROMANTIC_KEYWORDS = [
    re.compile(r"\b(forbidden\s+)?(love|romance|lovers|passion|romantic|dating)\b", re.IGNORECASE)
]


class StoryTruthValidator(BaseValidator):
    """Guarantees promotional representations do not manufacture false relationships or storylines."""

    def __init__(self):
        super().__init__("story_truth_validator")

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []

        # 1. Verify Canonical Relationships against text cards, promises, and creative strategy
        for rel in story_map.relationships:
            if rel.relationship_type == "siblings" and rel.immutable:
                # Biological siblings must never be marketed as lovers/romantic partners
                char_a = rel.character_a.lower()
                char_b = rel.character_b.lower()

                # Check trailer promise and strategy
                combined_text = f"{plan.audience_promise} {plan.creative_strategy} " + " ".join(
                    f"{s.text_card or ''} {s.reason or ''} {s.voice_over or ''}" for s in plan.segments
                )
                
                # If both characters are mentioned in connection with romance keywords
                if char_a in combined_text.lower() and char_b in combined_text.lower():
                    for kw_pattern in ROMANTIC_KEYWORDS:
                        if kw_pattern.search(combined_text):
                            results.append(
                                ValidationResultItem(
                                    validator=self.name,
                                    status=ValidationStatus.FAIL,
                                    severity=Severity.CRITICAL,
                                    message=f"Story truth violation: Manufactured false romance between canonical siblings "
                                            f"'{rel.character_a}' and '{rel.character_b}'. Evidence: {rel.canon_evidence}",
                                    evidence=[f"canon:{rel.character_a}-{rel.character_b}:{rel.relationship_type}", f"canon_evidence:{rel.canon_evidence}"],
                                    affected_segments=[s.segment_id for s in plan.segments if s.text_card and kw_pattern.search(s.text_card)],
                                    suggested_action=RepairAction.REPLACE_SEGMENT,
                                )
                            )

        # 2. Check for manufactured events not grounded in story map
        verified_scenes = {s.scene_id for s in story_map.scene_evidence}
        for seg in plan.segments:
            if seg.scene_id not in verified_scenes:
                results.append(
                    ValidationResultItem(
                        validator=self.name,
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Segment '{seg.segment_id}' references scene '{seg.scene_id}' not grounded in StoryMap evidence.",
                        evidence=[f"segment:{seg.segment_id}"],
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
                    message="Story truth verified: all relationships and events conform to canon.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
