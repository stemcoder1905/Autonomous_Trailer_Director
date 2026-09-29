"""Change Impact Analyzer and Selective Replanning Agent."""
from typing import List, Dict, Any, Optional
from src.models.schemas import (
    TrailerPlan,
    ChangeImpactReport,
    ConstraintRule,
    ConstraintMap,
    EpisodePackage,
    StoryMap,
)
from src.models.enums import ValidationStatus, ConstraintStatus
from src.agents.repair_agent import RepairAgent
from src.agents.validator_agent import IndependentValidationAgent
from src.utils.logger import logger, DecisionLogger


class ChangeImpactAgent:
    """Analyzes downstream effects of contract/policy modifications and selectively replans affected segments."""

    def __init__(
        self,
        validator_agent: Optional[IndependentValidationAgent] = None,
        repair_agent: Optional[RepairAgent] = None,
        decision_logger: Optional[DecisionLogger] = None
    ):
        self.validator_agent = validator_agent or IndependentValidationAgent()
        self.repair_agent = repair_agent or RepairAgent(validator_agent=self.validator_agent, decision_logger=decision_logger)
        self.decision_logger = decision_logger

    def analyze_and_replan(
        self,
        trailers: List[TrailerPlan],
        changed_rule: ConstraintRule,
        updated_constraint_map: ConstraintMap,
        package: EpisodePackage,
        story_map: StoryMap
    ) -> ChangeImpactReport:
        logger.info(
            f"[ChangeImpactAgent] Evaluating impact of contract rule '{changed_rule.rule_id}' "
            f"({changed_rule.scope}) with status '{changed_rule.status.value}'"
        )

        affected_trailers: List[str] = []
        unaffected_trailers: List[str] = []
        affected_segments_map: Dict[str, List[str]] = {}
        unaffected_segments_map: Dict[str, List[str]] = {}
        replan_reasons: List[str] = []
        validation_before: Dict[str, Any] = {}
        validation_after: Dict[str, Any] = {}
        old_decision: Dict[str, Any] = {}
        new_decision: Dict[str, Any] = {}

        target_scope = changed_rule.scope.split(":")[-1]  # e.g., 'music_03_synth_pulse' or 'scene_10'

        for plan in trailers:
            validation_before[plan.trailer_id] = plan.validation.status.value
            affected_in_this_plan: List[str] = []
            unaffected_in_this_plan: List[str] = []
            for seg in plan.segments:
                # Check if segment depends on changed music, scene, or actor
                if seg.music == target_scope:
                    affected_in_this_plan.append(seg.segment_id)
                elif seg.scene_id == target_scope:
                    affected_in_this_plan.append(seg.segment_id)
                else:
                    unaffected_in_this_plan.append(seg.segment_id)

            unaffected_segments_map[plan.trailer_id] = unaffected_in_this_plan

            if affected_in_this_plan:
                affected_trailers.append(plan.trailer_id)
                affected_segments_map[plan.trailer_id] = affected_in_this_plan
                old_decision[plan.trailer_id] = {
                    "asset": target_scope,
                    "affected_segments": list(affected_in_this_plan)
                }
                reason = (
                    f"Trailer '{plan.trailer_id}' references {changed_rule.type.value} '{target_scope}' "
                    f"in segments {affected_in_this_plan}. Triggered selective replanning."
                )
                replan_reasons.append(reason)
                logger.info(f"[ChangeImpactAgent] {reason}")

                # Selectively replan ONLY the affected segments using RepairAgent
                repaired_plan, success = self.repair_agent.attempt_repair(
                    plan, package, story_map, updated_constraint_map
                )
                # Overwrite segments in place for the affected trailer
                plan.segments = repaired_plan.segments
                plan.validation = repaired_plan.validation
                validation_after[plan.trailer_id] = plan.validation.status.value
                new_decision[plan.trailer_id] = {
                    "repaired_segments": [
                        {"segment_id": s.segment_id, "music": s.music, "scene_id": s.scene_id}
                        for s in plan.segments
                        if s.segment_id in affected_in_this_plan
                    ]
                }
            else:
                unaffected_trailers.append(plan.trailer_id)
                validation_after[plan.trailer_id] = plan.validation.status.value
                logger.info(f"[ChangeImpactAgent] Trailer '{plan.trailer_id}' has NO dependency on '{target_scope}'; left completely untouched.")

        overall_reason = (
            f"Constraint rule '{changed_rule.rule_id}' changed to {changed_rule.status.value}; "
            f"selectively replanned {len(affected_trailers)} affected trailers while preserving "
            f"{len(unaffected_trailers)} unaffected trailers completely intact."
        )

        new_statuses = {tid: ValidationStatus(status) for tid, status in validation_after.items()}

        report = ChangeImpactReport(
            change_id=f"change_{changed_rule.rule_id}",
            trigger=f"Rule '{changed_rule.rule_id}' changed to {changed_rule.status.value}",
            affected_trailers=affected_trailers,
            affected_segments=affected_segments_map,
            unaffected_trailers=unaffected_trailers,
            unaffected_segments=unaffected_segments_map,
            old_decision=old_decision,
            new_decision=new_decision,
            reason=overall_reason,
            replan_reasons=replan_reasons,
            validation_before=validation_before,
            validation_after=validation_after,
            new_validation_statuses=new_statuses
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="ChangeImpactAgent",
                action="SELECTIVE_REPLAN",
                reason=f"Selective replanning executed for {len(affected_trailers)} affected trailers; {len(unaffected_trailers)} preserved untouched.",
                input_evidence=[f"changed_rule:{changed_rule.rule_id}", f"status:{changed_rule.status.value}"],
                selected_decision={"affected": affected_trailers, "unaffected": unaffected_trailers},
                affected_segments=[seg for segs in affected_segments_map.values() for seg in segs],
                risk="LOW"
            )

        return report

