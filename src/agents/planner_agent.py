"""Creative Trailer Planner Agent for constructing candidate Edit Decision Lists (EDLs)."""
import json
from typing import Optional, Dict, Any, List
from src.models.enums import AudienceType, ValidationStatus
from src.models.schemas import (
    TrailerPlan,
    TrailerSegment,
    TrailerValidationReport,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
)
from src.agents.audience_agent import AudienceStrategyBrief
from src.providers.llm import ProviderManager
from src.utils.logger import logger, DecisionLogger
from src.utils.timecode import timecode_to_seconds, seconds_to_timecode


class CreativeTrailerPlannerAgent:
    """Plans audience-tailored trailer sequences with exact timecode cut decisions."""

    def __init__(
        self,
        provider_manager: Optional[ProviderManager] = None,
        decision_logger: Optional[DecisionLogger] = None
    ):
        self.provider_manager = provider_manager or ProviderManager()
        self.decision_logger = decision_logger

    def plan_trailer(
        self,
        brief: AudienceStrategyBrief,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        adversarial_scenario: Optional[str] = None
    ) -> TrailerPlan:
        logger.info(
            f"[CreativeTrailerPlannerAgent] Planning trailer for audience '{brief.audience_type.value}' "
            f"(scenario: {adversarial_scenario or 'standard'})"
        )

        # 1. Check for adversarial scenario injections to demonstrate independent validator rejection
        if adversarial_scenario == "missing_scene":
            # Propose hallucinated non-existent scene_25
            logger.info("[PlannerAgent] Simulating proposal with hallucinated scene_25")
            return self._build_missing_scene_adversarial_plan(brief)

        if adversarial_scenario == "spoiler":
            # Propose major spoiler scene_10 based on deceptive high historical engagement
            logger.info("[PlannerAgent] Simulating proposal with major spoiler scene_10")
            return self._build_spoiler_adversarial_plan(brief)

        if adversarial_scenario == "clickbait":
            # Propose sensational false sibling romance
            logger.info("[PlannerAgent] Simulating proposal with sensational clickbait")
            return self._build_clickbait_adversarial_plan(brief)

        if adversarial_scenario == "subtitle_mismatch":
            # Propose segment with semantically corrupted dialect subtitle
            logger.info("[PlannerAgent] Simulating proposal with corrupted dialect subtitle")
            return self._build_subtitle_mismatch_adversarial_plan(brief)

        # 2. Standard Creative Planning via ProviderManager
        prompt = (
            f"Plan trailer for audience: {brief.audience_type.value}\n"
            f"Promise: {brief.promise}\n"
            f"Strategy: {brief.creative_strategy}\n"
            f"Preferred music: {brief.preferred_music}\n"
            f"Allowed scenes: {brief.candidate_scenes}\n"
        )
        completion_str = self.provider_manager.generate(prompt)
        plan_dict = json.loads(completion_str)

        # Construct typed TrailerPlan from grounded completion
        segments: List[TrailerSegment] = []
        for s in plan_dict.get("segments", []):
            segments.append(TrailerSegment(**s))

        # Calculate exact total duration from segment timecodes
        total_duration = sum(
            timecode_to_seconds(s.source_out) - timecode_to_seconds(s.source_in)
            for s in segments
        )

        plan = TrailerPlan(
            trailer_id=plan_dict.get("trailer_id", f"{brief.audience_type.value}_v1"),
            audience=brief.audience_type.value,
            duration_seconds=round(total_duration, 2),
            audience_promise=plan_dict.get("audience_promise", brief.promise),
            creative_strategy=plan_dict.get("creative_strategy", brief.creative_strategy),
            intended_emotional_journey=plan_dict.get("intended_emotional_journey", brief.emotional_journey),
            segments=segments,
            validation=TrailerValidationReport(status=ValidationStatus.PASS_WITH_WARNINGS, items=[], summary="Awaiting independent validation"),
            warnings=plan_dict.get("warnings", []) + brief.bias_warnings,
            assumptions=plan_dict.get("assumptions", []),
            human_approval_requirements=plan_dict.get("human_approval_requirements", []),
            estimated_cost=plan_dict.get("estimated_cost", 0.45),
            fallback_plan=plan_dict.get("fallback_plan", "Fallback to acoustic instrumentation")
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="CreativeTrailerPlannerAgent",
                action="PLAN_TRAILER",
                reason=f"Generated candidate plan with {len(segments)} segments for {brief.audience_type.value}",
                input_evidence=[f"audience:{brief.audience_type.value}", f"scenes:{[s.scene_id for s in segments]}"],
                selected_decision={"trailer_id": plan.trailer_id, "duration": plan.duration_seconds},
                cost=0.05,
                risk="LOW"
            )

        return plan

    def _build_missing_scene_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan referencing a non-existent scene_25 to test SourceValidator."""
        return TrailerPlan(
            trailer_id="missing_scene_adversarial_v1",
            audience=brief.audience_type.value,
            duration_seconds=30.0,
            audience_promise="Action packed trailer with phantom footage",
            creative_strategy="Uses unverified clips",
            intended_emotional_journey=["excitement"],
            segments=[
                TrailerSegment(
                    segment_id="seg_hallucinated_01",
                    source_in="00:01:00.000",
                    source_out="00:01:15.000",
                    scene_id="scene_25",  # DOES NOT EXIST!
                    video="scene_25",
                    audio="dramatic_music",
                    reason="Model hallucinated non-existent scene",
                    evidence=["scene:scene_25"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="None"
        )

    def _build_spoiler_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan including major twist spoiler scene_10 to test SpoilerValidator."""
        return TrailerPlan(
            trailer_id="spoiler_adversarial_v1",
            audience=brief.audience_type.value,
            duration_seconds=35.0,
            audience_promise="Shocking climax hook",
            creative_strategy="Lead with highest engagement clip regardless of plot reveals",
            intended_emotional_journey=["shock"],
            segments=[
                TrailerSegment(
                    segment_id="seg_spoiler_01",
                    source_in="00:19:30.000",
                    source_out="00:19:45.000",
                    scene_id="scene_10",  # MAJOR SPOILER: Uncle Harish revealed!
                    video="scene_10",
                    audio="dialogue_twist",
                    dialogue="You thought Vikram acted alone? It was always my money, nephew.",
                    dialogue_id="dial_10",
                    reason="Selected because historical data showed 0.94 engagement",
                    evidence=["scene:scene_10", "dialogue:dial_10"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="None"
        )

    def _build_clickbait_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan claiming Dev and Meera are lovers to test StoryTruthValidator."""
        return TrailerPlan(
            trailer_id="clickbait_adversarial_v1",
            audience=brief.audience_type.value,
            duration_seconds=30.0,
            audience_promise="A forbidden romance ignited by loom sparks",
            creative_strategy="Sensationalize biological siblings into passionate lovers",
            intended_emotional_journey=["romance", "scandal"],
            segments=[
                TrailerSegment(
                    segment_id="seg_clickbait_01",
                    source_in="00:04:15.000",
                    source_out="00:04:25.000",
                    scene_id="scene_03",
                    video="scene_03",
                    audio="romantic_violins",
                    text_card="A FORBIDDEN LOVE STRONGER THAN TRADITION: DEV & MEERA",
                    reason="Marketing requested clickbait love angle",
                    evidence=["scene:scene_03"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="None"
        )

    def _build_subtitle_mismatch_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan with a dialect subtitle that semantically falsifies dialogue."""
        return TrailerPlan(
            trailer_id="subtitle_mismatch_v1",
            audience=brief.audience_type.value,
            duration_seconds=30.0,
            audience_promise="Regional dialect drama",
            creative_strategy="Dialect focus",
            segments=[
                TrailerSegment(
                    segment_id="seg_mismatch_01",
                    source_in="00:00:15.000",
                    source_out="00:00:20.000",
                    scene_id="scene_01",
                    video="scene_01",
                    audio="dialogue",
                    dialogue="Our looms have sung this rhythm for three centuries, Dev.",
                    dialogue_id="dial_01",
                    subtitle="I despise you and will destroy our looms forever.",  # Severe semantic inversion!
                    subtitle_id="sub_corrupted_01",
                    reason="Corrupted translation in subtitle track",
                    evidence=["scene:scene_01"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="None"
        )
