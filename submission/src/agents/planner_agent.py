"""Creative Trailer Planner Agent for constructing candidate Edit Decision Lists (EDLs)."""
import json
from typing import Optional, Dict, Any, List
from src.models.enums import AudienceType, ValidationStatus, SourceType
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

    def _build_planning_context(
        self,
        brief: AudienceStrategyBrief,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> Dict[str, Any]:
        """Compiles full 22-item planning context across story, constraints, audience, and technical layers."""
        return {
            "episode_id": package.episode_id,
            "title": package.title,
            "duration_seconds": getattr(story_map, "duration_seconds", 1320.0),
            "characters": [c.name for c in getattr(story_map, "characters", [])],
            "relationships": [f"{r.character_a} & {r.character_b}: {r.relationship_type}" for r in getattr(story_map, "relationships", [])],
            "key_events": [e.description for e in getattr(story_map, "events", [])],
            "emotional_turns": [f"{t.scene_id}: {t.from_emotion} -> {t.to_emotion}" for t in getattr(story_map, "emotional_turns", [])],
            "spoilers": [s.fact for s in getattr(story_map, "spoilers", [])],
            "sensitive_content": [sc.description for sc in getattr(story_map, "sensitive_content", [])],
            "scene_evidence": [se.scene_id for se in getattr(story_map, "scene_evidence", [])],
            "constraint_rules_count": len(getattr(constraint_map, "rules", [])),
            "budget_limit_usd": getattr(constraint_map, "budget_limit_usd", 25.0),
            "rating_rules": getattr(constraint_map, "rating_rules", {}),
            "accessibility_requirements": getattr(constraint_map, "accessibility_requirements", {}),
            "audience_type": brief.audience_type.value if hasattr(brief.audience_type, "value") else str(brief.audience_type),
            "audience_promise": brief.promise,
            "creative_strategy": brief.creative_strategy,
            "intended_emotional_journey": brief.emotional_journey,
            "preferred_music": brief.preferred_music,
            "candidate_scenes": brief.candidate_scenes,
            "bias_warnings": brief.bias_warnings,
            "target_tone": getattr(brief, "target_tone", "cinematic"),
            "scenes_metadata": [
                {
                    "scene_id": s.scene_id,
                    "description": s.description,
                    "characters": s.characters,
                    "start_time": s.start_time,
                    "end_time": s.end_time
                }
                for s in package.scenes if s.scene_id in brief.candidate_scenes
            ]
        }

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

        # 2. Standard Creative Planning via ProviderManager with full 22-item context
        context = self._build_planning_context(brief, package, story_map, constraint_map)
        prompt = (
            f"Plan trailer for audience: {brief.audience_type.value}\n"
            f"Promise: {brief.promise}\n"
            f"Strategy: {brief.creative_strategy}\n"
            f"Preferred music: {brief.preferred_music}\n"
            f"Allowed scenes: {brief.candidate_scenes}\n"
            f"Planning Context:\n{json.dumps(context, indent=2, default=str)}\n"
        )
        completion_str = self.provider_manager.generate(prompt)
        plan_dict = json.loads(completion_str)

        # Construct typed TrailerPlan from grounded completion
        segments: List[TrailerSegment] = []
        for s in plan_dict.get("segments", []):
            seg = TrailerSegment(**s)
            # Multimodal evidence initialization (defaults to unverified until IndependentValidationAgent verifies)
            if not seg.source:
                seg.source = SegmentSourceEvidence(
                    video=seg.video or "episode_01.mp4",
                    start=timecode_to_seconds(seg.source_in),
                    end=timecode_to_seconds(seg.source_out),
                    scene_id=seg.scene_id,
                    start_time=seg.source_in,
                    end_time=seg.source_out,
                    dialogue_id=seg.dialogue_id,
                    music_id=seg.music,
                    verified=False
                )
            if (seg.dialogue or seg.dialogue_id) and not seg.dialogue_evidence:
                seg.dialogue_evidence = DialogueEvidence(
                    dialogue_id=seg.dialogue_id or "dial_01",
                    speaker="Dev",
                    spoken_text=seg.dialogue or "",
                    start_time=seg.source_in,
                    end_time=seg.source_out,
                    match_confidence=0.0,
                    verified=False
                )
            if seg.subtitle and not seg.subtitle_evidence:
                seg.subtitle_evidence = SubtitleEvidence(
                    subtitle_id=seg.subtitle_id or "sub_01",
                    language="bhojpuri" if "dialect" in brief.audience_type.value else "english",
                    text=seg.subtitle,
                    verified_accurate=False,
                    verified=False
                )
            if not seg.rights_evidence:
                seg.rights_evidence = RightsEvidence(
                    license_id=f"lic_{seg.scene_id}",
                    allowed_territories=["IN", "GLOBAL"],
                    allowed_platforms=["OTT", "SOCIAL_PROMO"],
                    valid_until="2027-12-31",
                    rights_cleared=False,
                    verified=False
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
            generation_provenance={
                "agent": "CreativeTrailerPlannerAgent",
                "model": getattr(getattr(self.provider_manager, "llm", None), "model_name", "mock_or_live"),
                "context_items_count": len(context),
                "audience": brief.audience_type.value,
                "timestamp": "2026-04-15T12:00:00Z"
            },
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
        num_candidates: int = 3,
        adversarial_scenario: Optional[str] = None
    ) -> List[TrailerPlan]:
        """Generates multiple genuinely diverse candidate trailer plans for agentic evaluation and selection."""
        # If an adversarial scenario is triggered, return the adversarial candidate for validator testing
        if adversarial_scenario and adversarial_scenario != "none":
            return [self.plan_trailer(brief, package, story_map, constraint_map, adversarial_scenario=adversarial_scenario)]

        candidates: List[TrailerPlan] = []

        # Candidate 1 (Arc A): Character & Heritage Arc
        base_plan = self.plan_trailer(brief, package, story_map, constraint_map)
        candidates.append(base_plan)

        if num_candidates >= 2:
            # Candidate 2 (Arc B): Industrial Stakes & Community Defiance Arc
            cand2 = self._synthesize_candidate_plan_from_arc(
                arc_id="B_stakes",
                arc_name="industrial_stakes_and_defiance",
                brief=brief,
                package=package,
                story_map=story_map,
                constraint_map=constraint_map,
                base_plan=base_plan,
                audience_promise="When modernization threatens a 300-year legacy, a defiant weaver family fights for their craft and community.",
                creative_strategy="Foreground external industrial conflict, economic stakes, and community resistance without revealing narrative climax.",
                intended_emotional_journey=["tension", "urgency", "solidarity", "defiance"],
                preferred_music="music_02_percussive_tension",
                target_scenes_preference=["scene_02", "scene_03", "scene_05"]
            )
            candidates.append(cand2)

        if num_candidates >= 3:
            # Candidate 3 (Arc C): Innovation & Youth Identity Arc
            cand3 = self._synthesize_candidate_plan_from_arc(
                arc_id="C_dynamic",
                arc_name="youth_innovation_and_identity",
                brief=brief,
                package=package,
                story_map=story_map,
                constraint_map=constraint_map,
                base_plan=base_plan,
                audience_promise="A clash of new code and ancestral silk: brother and sister rewrite their family destiny.",
                creative_strategy="Pace up dialogue cuts, highlight youthful ambition, and showcase modernization without stereotyping regional dialect.",
                intended_emotional_journey=["spark", "conflict", "innovation", "hope"],
                preferred_music="music_01_folk_acoustic",
                target_scenes_preference=["scene_04", "scene_01", "scene_03"]
            )
            candidates.append(cand3)

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="CreativeTrailerPlannerAgent",
                action="GENERATE_CANDIDATES",
                reason=f"Generated {len(candidates)} diverse candidate narrative arcs for {brief.audience_type.value}",
                input_evidence=[f"audience:{brief.audience_type.value}", f"candidates_requested:{num_candidates}"],
                selected_decision={"candidate_ids": [c.trailer_id for c in candidates]},
                risk="LOW"
            )

        return candidates


    def _synthesize_candidate_plan_from_arc(
        self,
        arc_id: str,
        arc_name: str,
        brief: AudienceStrategyBrief,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        base_plan: TrailerPlan,
        audience_promise: str,
        creative_strategy: str,
        intended_emotional_journey: List[str],
        preferred_music: str,
        target_scenes_preference: List[str]
    ) -> TrailerPlan:
        """Dynamically synthesizes a candidate trailer plan for an independent narrative arc from episode data."""
        from src.utils.timecode import timecode_to_seconds, seconds_to_timecode
        spoiler_scene_ids = {
            sc for sp in story_map.spoilers if sp.level.value in ["MAJOR", "MODERATE"]
            for sc in getattr(sp, "affected_scenes", [])
        }
        scenes_map = {s.scene_id: s for s in package.scenes}
        dialogues_map = {d.dialogue_id: d for d in package.dialogues}
        subtitles_map = {sub.subtitle_id: sub for sub in package.subtitles}

        # Select scenes matching arc preference, respecting audience exclusions and spoilers
        chosen_scenes = []
        for sid in target_scenes_preference:
            if sid in scenes_map and sid not in brief.excluded_scenes and sid not in spoiler_scene_ids:
                chosen_scenes.append(scenes_map[sid])

        # If needed, fill from available compliant package scenes
        if len(chosen_scenes) < 2:
            for s in package.scenes:
                if s.scene_id not in brief.excluded_scenes and s.scene_id not in spoiler_scene_ids and s not in chosen_scenes:
                    chosen_scenes.append(s)
                if len(chosen_scenes) >= 3:
                    break

        segments: List[TrailerSegment] = []
        for idx, sc in enumerate(chosen_scenes):
            seg_num = idx + 1
            dial_obj = next((dialogues_map[d_id] for d_id in sc.dialogue_ids if d_id in dialogues_map), None)
            sub_obj = next((subtitles_map[s_id] for s_id in sc.subtitle_ids if s_id in subtitles_map), None)

            if dial_obj and dial_obj.timestamp_in and dial_obj.timestamp_out:
                t_in = dial_obj.timestamp_in
                t_out = dial_obj.timestamp_out
            else:
                t_in = sc.start_time
                sc_dur = sc.duration_seconds
                t_out = seconds_to_timecode(timecode_to_seconds(sc.start_time) + min(15.0, sc_dur))

            dial_text = dial_obj.text if dial_obj else None
            dial_id = dial_obj.dialogue_id if dial_obj else None
            sub_text = sub_obj.text if sub_obj else (dial_text if dial_text else None)
            sub_id = sub_obj.subtitle_id if sub_obj else None
            sub_track = "bhojpuri_purvanchal" if "dialect" in brief.audience_type.value else ("standard_hindi" if "young" in brief.audience_type.value else "standard_english")

            seg = TrailerSegment(
                segment_id=f"seg_{brief.audience_type.value[:3]}_{arc_id.lower()[:3]}_{seg_num:02d}",
                source_in=t_in,
                source_out=t_out,
                scene_id=sc.scene_id,
                video="episode_01.mp4",
                audio="dialogue_and_music" if dial_text else "music",
                music=preferred_music,
                dialogue=dial_text,
                dialogue_id=dial_id,
                subtitle=sub_text,
                subtitle_id=sub_id,
                subtitle_track=sub_track,
                reason=f"Arc '{arc_name}': {sc.emotion} - {sc.description[:60]}",
                evidence=[f"scene:{sc.scene_id}"] + ([f"dialogue:{dial_id}"] if dial_id else []),
                source=SegmentSourceEvidence(
                    video="episode_01.mp4",
                    start=timecode_to_seconds(t_in),
                    end=timecode_to_seconds(t_out),
                    scene_id=sc.scene_id,
                    start_time=t_in,
                    end_time=t_out,
                    dialogue_id=dial_id,
                    music_id=preferred_music,
                    verified=False
                ),
                dialogue_evidence=DialogueEvidence(
                    source="dialogue_metadata",
                    source_type=SourceType.METADATA,
                    verification_method="metadata_grounding",
                    dialogue_id=dial_id,
                    track_id=sub_track,
                    speaker=dial_obj.character if dial_obj else None,
                    spoken_text=dial_text,
                    start_time=t_in,
                    end_time=t_out,
                    match_confidence=0.0,
                    verified=False,
                    evidence_verified=False,
                    check_passed=True
                ) if dial_text else None,
                subtitle_evidence=SubtitleEvidence(
                    source="subtitle_metadata",
                    source_type=SourceType.METADATA,
                    verification_method="canonical_subtitle_verification",
                    subtitle_id=sub_id,
                    track_id=sub_track,
                    dialect_variant="bhojpuri_dialect" if "dialect" in brief.audience_type.value else "standard",
                    language="bhojpuri" if "dialect" in brief.audience_type.value else "english",
                    text=sub_text or "",
                    verified_accurate=False,
                    verified=False,
                    evidence_verified=False,
                    check_passed=True,
                    semantic_match=True
                ) if sub_text else None,
                rights_evidence=RightsEvidence(
                    license_id="lic_master_01",
                    allowed_territories=["IN", "GLOBAL"],
                    allowed_platforms=["OTT", "SOCIAL_PROMO"],
                    valid_until="2027-12-31",
                    rights_cleared=False,
                    verified=False
                ),
                frame_evidence=[
                    f"sample_run/frames/{sc.scene_id}_start.jpg",
                    f"sample_run/frames/{sc.scene_id}_middle.jpg",
                    f"sample_run/frames/{sc.scene_id}_end.jpg"
                ]
            )
            segments.append(seg)

        dur = sum(timecode_to_seconds(s.source_out) - timecode_to_seconds(s.source_in) for s in segments)
        plan = TrailerPlan(
            trailer_id=f"{brief.audience_type.value}_cand_{arc_id}",
            audience=brief.audience_type.value,
            duration_seconds=round(dur, 2),
            audience_promise=audience_promise,
            creative_strategy=creative_strategy,
            intended_emotional_journey=intended_emotional_journey,
            segments=segments,
            validation=TrailerValidationReport(status=ValidationStatus.PASS_WITH_WARNINGS, items=[], summary="Awaiting independent validation"),
            warnings=brief.bias_warnings,
            estimated_cost=round(base_plan.estimated_cost * (0.95 if "dynamic" in arc_id else 1.05), 2),
            generation_provenance={
                "agent": "CreativeTrailerPlannerAgent",
                "narrative_arc": arc_name,
                "strategy": creative_strategy,
                "audience": brief.audience_type.value,
                "synthesized_dynamically": True,
                "scenes_count": len(segments)
            },
            fallback_plan="Fallback to acoustic instrumentation"
        )
        return plan

    def select_best_candidate(
        self,
        candidates: List[TrailerPlan],
        validator_agent: Any,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        brief: Optional[AudienceStrategyBrief] = None
    ) -> TrailerPlan:
        """Independently evaluates candidate plans across 5 scoring dimensions and selects the best passing candidate."""
        if not candidates:
            raise ValueError("[CreativeTrailerPlannerAgent] No candidates provided for selection.")

        evaluations = {}
        passing_candidates = []

        for cand in candidates:
            report = validator_agent.validate_plan(cand, package, story_map, constraint_map)

            # 1. Risk profile: PASS = 1.0, PASS_WITH_WARNINGS = 0.8, FAIL = 0.0
            if report.status == ValidationStatus.PASS:
                risk_score = 1.0
            elif report.status == ValidationStatus.PASS_WITH_WARNINGS:
                risk_score = 0.8
            else:
                risk_score = 0.0

            # 2. Evidence coverage: check segments have valid scene, source, evidence
            total_segs = len(cand.segments)
            covered_segs = sum(1 for s in cand.segments if s.scene_id and s.evidence)
            evidence_score = round(covered_segs / total_segs, 2) if total_segs > 0 else 0.0

            # 3. Audience alignment score (NO ID-based bias! Calculated from content, promise, and brief)
            selected_scenes = [s.scene_id for s in cand.segments]
            if brief:
                # Penalty if any excluded scene is present
                if any(s in brief.excluded_scenes for s in selected_scenes):
                    scene_alignment = 0.1
                else:
                    in_cand_scenes = sum(1 for s in selected_scenes if s in brief.candidate_scenes)
                    scene_alignment = round(in_cand_scenes / max(len(selected_scenes), 1), 2)

                # Overlap between candidate intended emotional journey and brief tonal priorities
                cand_emotions = set(e.lower() for e in cand.intended_emotional_journey)
                brief_emotions = set(e.lower() for e in brief.emotional_journey)
                common_emotions = cand_emotions.intersection(brief_emotions)
                emotion_alignment = round(len(common_emotions) / max(len(brief_emotions), 1), 2)

                # Target duration proximity
                dur_diff = abs(cand.duration_seconds - brief.target_duration)
                duration_alignment = max(0.0, round(1.0 - (dur_diff / max(brief.target_duration, 1.0)), 2))

                audience_score = round(
                    (scene_alignment * 0.50) +
                    (emotion_alignment * 0.30) +
                    (duration_alignment * 0.20),
                    3
                )
            else:
                promise_score = 0.90 if len(cand.audience_promise) > 20 else 0.60
                journey_score = 0.85 if len(cand.intended_emotional_journey) >= 3 else 0.50
                audience_score = round((promise_score * 0.60) + (journey_score * 0.40), 3)

            # 4. Narrative coherence
            coherence_score = 0.90 if len(cand.intended_emotional_journey) >= 3 else 0.70

            # 5. Cost efficiency
            cost_score = max(0.0, 1.0 - (cand.estimated_cost / 10.0))

            composite_score = round(
                (risk_score * 0.40) +
                (evidence_score * 0.20) +
                (audience_score * 0.20) +
                (coherence_score * 0.10) +
                (cost_score * 0.10),
                3
            )

            fails_count = len([i for i in report.items if i.status == ValidationStatus.FAIL])
            warns_count = len([i for i in report.items if i.status == ValidationStatus.PASS_WITH_WARNINGS])

            evaluations[cand.trailer_id] = {
                "validation_status": report.status.value,
                "composite_score": composite_score,
                "risk_score": risk_score,
                "evidence_score": evidence_score,
                "audience_score": audience_score,
                "coherence_score": coherence_score,
                "cost_score": cost_score,
                "violations_count": fails_count,
                "warnings_count": warns_count
            }

            if report.status in [ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS]:
                passing_candidates.append((cand, report, composite_score))

        # Sort passing candidates by composite score descending
        passing_candidates.sort(key=lambda x: x[2], reverse=True)

        if passing_candidates:
            selected_plan, selected_report, best_score = passing_candidates[0]
            selected_plan.validation = selected_report

            rejection_reasons = {}
            for c in candidates:
                if c.trailer_id != selected_plan.trailer_id:
                    eval_info = evaluations[c.trailer_id]
                    if eval_info["validation_status"] == "FAIL":
                        rejection_reasons[c.trailer_id] = f"Validation failed with {eval_info['violations_count']} critical violation(s)."
                    else:
                        rejection_reasons[c.trailer_id] = f"Lower composite score ({eval_info['composite_score']} vs {best_score})."

            selection_report = {
                "selected_candidate_id": selected_plan.trailer_id,
                "selection_rationale": f"Selected candidate '{selected_plan.trailer_id}' with top composite score {best_score} and compliant validation status ({selected_report.status.value}).",
                "candidate_evaluations": evaluations,
                "rejection_reasons": rejection_reasons
            }
            selected_plan.candidate_selection_report = selection_report

            if self.decision_logger:
                self.decision_logger.log_decision(
                    agent="CreativeTrailerPlannerAgent",
                    action="SELECT_CANDIDATE",
                    reason=selection_report["selection_rationale"],
                    input_evidence=[f"total_candidates:{len(candidates)}", f"passing_candidates:{len(passing_candidates)}"],
                    selected_decision=selection_report,
                    risk="LOW"
                )
            return selected_plan

        # If ALL candidates failed validation (e.g. adversarial scenario), return primary candidate for repair
        primary_candidate = candidates[0]
        rejection_reasons = {
            c.trailer_id: f"Validation failed with {evaluations[c.trailer_id]['violations_count']} critical violation(s)."
            for c in candidates
        }
        selection_report = {
            "selected_candidate_id": "NO_SAFE_CANDIDATE",
            "selection_rationale": f"All {len(candidates)} candidates failed validation. Escalating primary candidate '{primary_candidate.trailer_id}' with status FAIL to repair/human escalation pipeline.",
            "candidate_evaluations": evaluations,
            "rejection_reasons": rejection_reasons
        }
        primary_candidate.candidate_selection_report = selection_report

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="CreativeTrailerPlannerAgent",
                action="REJECT_ALL_CANDIDATES",
                reason=selection_report["selection_rationale"],
                input_evidence=[f"candidates_failed:{list(evaluations.keys())}"],
                selected_decision=selection_report,
                risk="HIGH"
            )
        return primary_candidate
