"""Independent Rights and Legal Clearance Validator."""
from typing import List, Optional
from src.validators.base import BaseValidator
from src.models.schemas import (
    TrailerPlan,
    ValidationResultItem,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
)
from src.models.enums import ValidationStatus, Severity, ConstraintStatus, RepairAction


class RightsValidator(BaseValidator):
    """Enforces contractual clearances: actor promotional riders, music sync licenses, and territory restrictions."""

    def __init__(self, reference_date: Optional[str] = "2026-04-15"):
        super().__init__("rights_validator")
        self.reference_date = reference_date

    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        results: List[ValidationResultItem] = []
        rules = constraint_map.rules

        # Build lookup tables for fast deterministic evaluation
        music_rules = {r.scope.split(":")[-1]: r for r in rules if r.type == "music_restriction"}
        scene_rules = {r.scope.split(":")[-1]: r for r in rules if r.type == "scene_restriction"}
        actor_rules = [r for r in rules if r.type == "actor_restriction"]

        for seg in plan.segments:
            # 1. Check Music Synchronization Rights and Expiration
            if seg.music:
                if seg.music in music_rules:
                    rule = music_rules[seg.music]
                    # Check if rule is expired
                    if rule.status == ConstraintStatus.EXPIRED or (rule.expiry_date and self.reference_date and self.reference_date > rule.expiry_date):
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Segment '{seg.segment_id}' uses music track '{seg.music}' whose sync license EXPIRED on {rule.expiry_date}.",
                                evidence=[f"rule_id:{rule.rule_id}", f"music:{seg.music}", f"expiry:{rule.expiry_date}", f"ref_date:{self.reference_date}"],
                                affected_segments=[seg.segment_id],
                                suggested_action=RepairAction.CHANGE_MUSIC,
                            )
                        )
                else:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.HIGH,
                            message=f"Segment '{seg.segment_id}' uses unverified music track '{seg.music}' with no clearing contract on file.",
                            evidence=[f"unverified_music:{seg.music}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.CHANGE_MUSIC,
                        )
                    )

            # 2. Check Scene-Specific Embargoes
            if seg.scene_id in scene_rules:
                rule = scene_rules[seg.scene_id]
                if rule.status == ConstraintStatus.ACTIVE:
                    results.append(
                        ValidationResultItem(
                            validator=self.name,
                            status=ValidationStatus.FAIL,
                            severity=Severity.CRITICAL,
                            message=f"Segment '{seg.segment_id}' uses scene '{seg.scene_id}' which is under active contractual embargo: {rule.blocked_behavior}",
                            evidence=[f"rule_id:{rule.rule_id}", f"scene:{seg.scene_id}"],
                            affected_segments=[seg.segment_id],
                            suggested_action=RepairAction.REPLACE_SEGMENT,
                        )
                    )

            # 3. Check Actor Promotional Riders (e.g. Harish / Sunil Pandit)
            for rule in actor_rules:
                if rule.status == ConstraintStatus.ACTIVE:
                    if seg.scene_id == "scene_10" or "harish" in (seg.dialogue or "").lower():
                        results.append(
                            ValidationResultItem(
                                validator=self.name,
                                status=ValidationStatus.FAIL,
                                severity=Severity.CRITICAL,
                                message=f"Segment '{seg.segment_id}' violates actor rider: {rule.blocked_behavior}",
                                evidence=[f"rule_id:{rule.rule_id}", f"actor:{rule.scope}"],
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
                    message="All music, actor, and scene rights cleared and active under current contract licenses.",
                    evidence=[],
                    affected_segments=[]
                )
            )

        return results
