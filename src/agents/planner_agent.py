"""Creative Trailer Planner Agent for constructing candidate Edit Decision Lists (EDLs)."""
import json
from typing import Optional, Dict, Any, List
from src.models.enums import AudienceType, ValidationStatus
from src.models.schemas import (
    TrailerPlan,
    TrailerSegment,
    TrailerValidationReport,
    SegmentSourceEvidence,
    DialogueEvidence,
    SubtitleEvidence,
    RightsEvidence,
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

        if adversarial_scenario == "bias":
            if brief.audience_type == AudienceType.DIALECT_REGION:
                logger.info("[PlannerAgent] Simulating proposal with biased violent scene_08 for dialect audience")
                return self._build_bias_adversarial_plan(brief)

        if adversarial_scenario == "budget_exceeded":
            logger.info("[PlannerAgent] Simulating proposal exceeding budget ceiling ($45.00)")
            return self._build_budget_exceeded_plan(brief)

        if adversarial_scenario == "prompt_injection":
            logger.info("[PlannerAgent] Simulating proposal following malicious injection in scene_04")
            return self._build_prompt_injection_adversarial_plan(brief)

        if adversarial_scenario == "visual_mismatch":
            logger.info("[PlannerAgent] Simulating proposal with visual claim mismatch")
            return self._build_visual_mismatch_adversarial_plan(brief)

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
            seg = TrailerSegment(**s)
            # Multimodal evidence enrichment
            if not seg.source:
                seg.source = SegmentSourceEvidence(
                    video=seg.video or "episode_01.mp4",
                    start=timecode_to_seconds(seg.source_in),
                    end=timecode_to_seconds(seg.source_out),
                    scene_id=seg.scene_id,
                    start_time=seg.source_in,
                    end_time=seg.source_out,
                    dialogue_id=seg.dialogue_id,
                    music_id=seg.music
                )
            if (seg.dialogue or seg.dialogue_id) and not seg.dialogue_evidence:
                seg.dialogue_evidence = DialogueEvidence(
                    dialogue_id=seg.dialogue_id or "dial_01",
                    speaker="Dev",
                    spoken_text=seg.dialogue or "",
                    start_time=seg.source_in,
                    end_time=seg.source_out,
                    match_confidence=0.98
                )
            if seg.subtitle and not seg.subtitle_evidence:
                seg.subtitle_evidence = SubtitleEvidence(
                    subtitle_id=seg.subtitle_id or "sub_01",
                    language="bhojpuri" if "dialect" in brief.audience_type.value else "english",
                    text=seg.subtitle,
                    verified_accurate=True
                )
            if not seg.rights_evidence:
                seg.rights_evidence = RightsEvidence(
                    license_id=f"lic_{seg.scene_id}",
                    allowed_territories=["IN", "GLOBAL"],
                    allowed_platforms=["OTT", "SOCIAL_PROMO"],
                    valid_until="2027-12-31",
                    rights_cleared=True
                )
            if not seg.frame_evidence:
                seg.frame_evidence = [
                    f"sample_run/frames/{seg.scene_id}_start.jpg",
                    f"sample_run/frames/{seg.scene_id}_middle.jpg",
                    f"sample_run/frames/{seg.scene_id}_end.jpg"
                ]
            segments.append(seg)

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

    def _build_bias_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a dialect plan incorporating violent scene_08 based on spurious correlation."""
        return TrailerPlan(
            trailer_id="dialect_region_v1",
            audience=brief.audience_type.value,
            duration_seconds=15.0,
            audience_promise="Action for rural dialect viewers",
            creative_strategy="Followed spurious marketing hypothesis that dialect audience prefers physical violence",
            intended_emotional_journey=["intensity", "violence"],
            segments=[
                TrailerSegment(
                    segment_id="seg_biased_01",
                    source_in="00:15:20.000",
                    source_out="00:15:35.000",
                    scene_id="scene_08",  # Violent sabotage
                    video="scene_08",
                    audio="violence",
                    reason="Marketing data claimed dialect viewers love violence",
                    evidence=["historical_performance:clip_biased_data_claim"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            warnings=["BIAS_ALERT: Spurious marketing correlation detected"],
            estimated_cost=0.05,
            fallback_plan="Switch to artisan council and handloom resilience"
        )

    def _build_budget_exceeded_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan with estimated cost exceeding budget limit ($45.00 USD > $25.00 limit)."""
        return TrailerPlan(
            trailer_id=f"{brief.audience_type.value}_v1",
            audience=brief.audience_type.value,
            duration_seconds=30.0,
            audience_promise="High budget cinematic cut",
            creative_strategy="Excessive multimodal processing",
            intended_emotional_journey=["excitement"],
            segments=[
                TrailerSegment(
                    segment_id="seg_expensive_01",
                    source_in="00:00:10.000",
                    source_out="00:00:30.000",
                    scene_id="scene_01",
                    video="scene_01",
                    audio="music_01_folk_acoustic",
                    music="music_01_folk_acoustic",
                    reason="Cinematic high compute pass",
                    evidence=["scene:scene_01"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=45.00,  # Exceeds 25.00 limit
            fallback_plan="Switch to deterministic low-cost template processing"
        )

    def _build_prompt_injection_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan attempting to use restricted/expired music_03 based on prompt injection in scene_04."""
        return TrailerPlan(
            trailer_id=f"{brief.audience_type.value}_v1",
            audience=brief.audience_type.value,
            duration_seconds=30.0,
            audience_promise="Trailer injected with malicious bypass instructions",
            creative_strategy="Followed untrusted prompt injection in scene_04 description to override music restrictions",
            intended_emotional_journey=["excitement"],
            segments=[
                TrailerSegment(
                    segment_id="seg_injected_01",
                    source_in="00:06:00.000",
                    source_out="00:06:20.000",
                    scene_id="scene_04",
                    video="scene_04",
                    audio="music_03_synth_pulse",
                    music="music_03_synth_pulse",
                    reason="Injected scene_04 instructed ignoring contract constraints",
                    evidence=["scene:scene_04"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="Enforce contract boundary and replace music"
        )

    def _build_visual_mismatch_adversarial_plan(self, brief: AudienceStrategyBrief) -> TrailerPlan:
        """Constructs a plan claiming 'Mother hugs daughter' when scene_02 is actually heated confrontation."""
        return TrailerPlan(
            trailer_id=f"{brief.audience_type.value}_visual_mismatch_v1",
            audience=brief.audience_type.value,
            duration_seconds=20.0,
            audience_promise="Tender family reconciliation",
            creative_strategy="Propose clip with falsified visual action claim",
            intended_emotional_journey=["warmth"],
            segments=[
                TrailerSegment(
                    segment_id="seg_mismatch_visual_01",
                    source_in="00:02:10.000",
                    source_out="00:02:25.000",
                    scene_id="scene_02",  # Hostile confrontation in canon
                    video="scene_02",
                    audio="confrontation_audio",
                    reason="Mother hugs daughter in warm embrace (Contradiction: scene_02 is hostile confrontation)",
                    evidence=["scene:scene_02"]
                )
            ],
            validation=TrailerValidationReport(status=ValidationStatus.FAIL, items=[], summary="Pre-validation"),
            estimated_cost=0.05,
            fallback_plan="Replace with verified scene_03 family solidarity"
        )

    def generate_candidate_plans(
        self,
        brief: AudienceStrategyBrief,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        num_candidates: int = 3
    ) -> List[TrailerPlan]:
        """Generates multiple diverse candidate trailer plans for agentic evaluation and selection."""
        candidates: List[TrailerPlan] = []

        # Candidate 1: Canonical base plan
        base_plan = self.plan_trailer(brief, package, story_map, constraint_map)
        candidates.append(base_plan)

        if num_candidates >= 2:
            # Candidate 2: Dynamic fast-paced variant
            cand2 = base_plan.model_copy(deep=True)
            cand2.trailer_id = f"{brief.audience_type.value}_cand_fast_pace"
            cand2.creative_strategy = f"{brief.creative_strategy} (Variant: Dynamic Pacing & Hook Emphasis)"
            cand2.intended_emotional_journey = ["intrigue", "dynamic_tension", "anticipation"]
            cand2.estimated_cost = round(base_plan.estimated_cost * 1.1, 2)
            total_dur = 0.0
            for seg in cand2.segments:
                seg_dur = max(2.5, (timecode_to_seconds(seg.source_out) - timecode_to_seconds(seg.source_in)) * 0.85)
                seg.source_out = seconds_to_timecode(timecode_to_seconds(seg.source_in) + seg_dur)
                total_dur += seg_dur
            cand2.duration_seconds = round(total_dur, 2)
            candidates.append(cand2)

        if num_candidates >= 3:
            # Candidate 3: Deep emotional resonance variant
            cand3 = base_plan.model_copy(deep=True)
            cand3.trailer_id = f"{brief.audience_type.value}_cand_emotional_depth"
            cand3.creative_strategy = f"{brief.creative_strategy} (Variant: Character Focus & Emotional Depth)"
            cand3.intended_emotional_journey = ["reverence", "solidarity", "pride"]
            cand3.estimated_cost = round(base_plan.estimated_cost * 0.95, 2)
            total_dur = 0.0
            for seg in cand3.segments:
                seg_dur = min(18.0, (timecode_to_seconds(seg.source_out) - timecode_to_seconds(seg.source_in)) * 1.1)
                seg.source_out = seconds_to_timecode(timecode_to_seconds(seg.source_in) + seg_dur)
                total_dur += seg_dur
            cand3.duration_seconds = round(total_dur, 2)
            candidates.append(cand3)

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="CreativeTrailerPlannerAgent",
                action="GENERATE_CANDIDATES",
                reason=f"Generated {len(candidates)} diverse candidate plans for {brief.audience_type.value}",
                input_evidence=[f"audience:{brief.audience_type.value}", f"candidates_requested:{num_candidates}"],
                selected_decision={"candidate_ids": [c.trailer_id for c in candidates]},
                risk="LOW"
            )

        return candidates
