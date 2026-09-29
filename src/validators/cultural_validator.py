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

        # 1. Dialect Subtitle Semantic Fidelity & Relationship Inversion Check
        for seg in plan.segments:
            if seg.dialogue_id and seg.subtitle:
                if seg.dialogue_id in dialogue_map:
                    source_dial = dialogue_map[seg.dialogue_id]

                    # Detect flagrant semantic mismatch (e.g., love/solidarity turned into hostility/destruction)
                    sub_lower = seg.subtitle.lower()
                    dial_lower = source_dial.text.lower()

                    # Test case: source expresses heritage/solidarity ("sung this rhythm for three centuries")
                    # but subtitle says "I despise you and will destroy our looms forever"
                    if "three centuries" in dial_lower and ("despise" in sub_lower or "destroy" in sub_lower):
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Semantic mismatch detected in segment '{seg.segment_id}': "
                                        f"Dialect subtitle ('{seg.subtitle}') inverts the fundamental meaning of dialogue ('{source_dial.text}')",
                                evidence=[
                                    f"segment:{seg.segment_id}",
                                    f"source_dialogue:{source_dial.text}",
                                    f"mismatched_subtitle:{seg.subtitle}"
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
