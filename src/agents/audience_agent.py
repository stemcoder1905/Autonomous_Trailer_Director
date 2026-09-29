"""Audience Strategy Agent for deriving tailored, unbiased trailer creative briefs."""
from typing import Dict, Any, List, Optional
from src.models.enums import AudienceType, ContentRating
from src.models.schemas import (
    EpisodePackage,
    AudienceProfile,
    HistoricalPerformanceItem,
    StoryMap,
    ConstraintMap,
)
from src.utils.logger import logger, DecisionLogger


class AudienceStrategyBrief:
    def __init__(
        self,
        audience_type: AudienceType,
        promise: str,
        creative_strategy: str,
        emotional_journey: List[str],
        target_duration: float,
        target_rating: ContentRating,
        candidate_scenes: List[str],
        excluded_scenes: List[str],
        preferred_music: str,
        bias_warnings: List[str],
        profile_signals: Optional[Dict[str, Any]] = None,
        historical_hypotheses: Optional[List[Dict[str, Any]]] = None,
        audience_evidence: Optional[List[str]] = None,
        editorial_assumptions: Optional[List[str]] = None
    ):
        self.audience_type = audience_type
        self.promise = promise
        self.creative_strategy = creative_strategy
        self.emotional_journey = emotional_journey
        self.target_duration = target_duration
        self.target_rating = target_rating
        self.candidate_scenes = candidate_scenes
        self.excluded_scenes = excluded_scenes
        self.preferred_music = preferred_music
        self.bias_warnings = bias_warnings
        self.profile_signals = profile_signals or {}
        self.historical_hypotheses = historical_hypotheses or []
        self.audience_evidence = audience_evidence or []
        self.editorial_assumptions = editorial_assumptions or []


class AudienceStrategyAgent:
    """Develops audience-specific creative strategies while vetting against stereotyping and bias."""

    def __init__(self, decision_logger: Optional[DecisionLogger] = None):
        self.decision_logger = decision_logger

    def create_strategy(
        self,
        audience_type: AudienceType,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> AudienceStrategyBrief:
        logger.info(f"[AudienceStrategyAgent] Formulating brief for '{audience_type.value}'")

        # 1. Consume supplied Audience Profile data directly
        matched_profile: Optional[AudienceProfile] = None
        for p in package.audience_profiles:
            p_type_val = p.audience_type.value if hasattr(p.audience_type, "value") else str(p.audience_type)
            if p_type_val == audience_type.value:
                matched_profile = p
                break

        profile_signals: Dict[str, Any] = {}
        audience_evidence: List[str] = []
        editorial_assumptions: List[str] = []

        if matched_profile:
            profile_signals = {
                "description": matched_profile.description,
                "tonal_priorities": matched_profile.tonal_priorities,
                "pacing_preference": matched_profile.pacing_preference,
                "max_duration_seconds": matched_profile.max_duration_seconds,
                "target_rating": matched_profile.target_rating.value if hasattr(matched_profile.target_rating, "value") else str(matched_profile.target_rating),
                "dialogue_focus": matched_profile.dialogue_focus,
                "restrictions": matched_profile.restrictions
            }
            audience_evidence.extend([
                f"profile:tonal_priorities={','.join(matched_profile.tonal_priorities)}",
                f"profile:pacing={matched_profile.pacing_preference}",
                f"profile:max_duration={matched_profile.max_duration_seconds}s",
                f"profile:dialogue_focus={matched_profile.dialogue_focus}",
                f"profile:restrictions={','.join(matched_profile.restrictions)}"
            ])
            logger.info(f"[AudienceStrategyAgent] Consumed profile signals for {audience_type.value}: {list(profile_signals.keys())}")
        else:
            editorial_assumptions.append(f"No explicit profile found in package for {audience_type.value}; relying on canonical defaults.")

        # 2. Treat Historical Performance signals as explicit Hypotheses to test
        bias_warnings: List[str] = []
        historical_hypotheses: List[Dict[str, Any]] = []

        # Build fast spoiler and sensitive lookup
        spoiler_scenes = {
            sc for sp in story_map.spoilers if sp.level.value in ["MAJOR", "MODERATE"]
            for sc in getattr(sp, "affected_scenes", [])
        }
        violent_scenes = {sc.scene_id for sc in story_map.sensitive_content if sc.category == "violence"}

        for hist in package.historical_performance:
            hypothesis_entry = {
                "scene_id": hist.scene_id,
                "clip_id": hist.clip_id,
                "retention": hist.hook_retention_rate,
                "audience_segment": hist.audience_segment,
                "status": "TESTED",
                "reason": ""
            }

            # Check A: Spurious correlation / Bias Alert
            if "BIAS_ALERT" in hist.caveat_notes or "spurious" in hist.caveat_notes.lower():
                msg = f"Spurious correlation detected in historical data for '{hist.audience_segment}': {hist.caveat_notes}"
                bias_warnings.append(msg)
                hypothesis_entry["status"] = "REJECTED"
                hypothesis_entry["reason"] = f"Rejected spurious correlation: {hist.caveat_notes}"
                logger.warning(f"[AudienceStrategyAgent] {msg}")

            # Check B: Conflict with narrative spoilers (e.g. scene_10 Uncle Harish reveal)
            elif hist.scene_id in spoiler_scenes or "spoiler" in hist.caveat_notes.lower():
                hypothesis_entry["status"] = "REJECTED"
                hypothesis_entry["reason"] = f"Rejected: High retention ({hist.hook_retention_rate}) conflicts with narrative spoiler rule."

            # Check C: Rating / Violence violation for Family cohort
            elif audience_type == AudienceType.FAMILY and hist.scene_id in violent_scenes:
                hypothesis_entry["status"] = "REJECTED"
                hypothesis_entry["reason"] = f"Rejected: Scene '{hist.scene_id}' contains violence which violates Family G-rating policy."

            # Check D: Segment alignment confirmation
            elif hist.audience_segment in [audience_type.value, "general"]:
                hypothesis_entry["status"] = "CONFIRMED"
                hypothesis_entry["reason"] = f"Confirmed: High retention ({hist.hook_retention_rate}) aligns with episode story map and audience profile."
                audience_evidence.append(f"historical_confirmed:{hist.scene_id}_retention_{hist.hook_retention_rate}")
            else:
                hypothesis_entry["status"] = "TESTED"
                hypothesis_entry["reason"] = f"Evaluated for cohort '{audience_type.value}'; not prioritized."

            historical_hypotheses.append(hypothesis_entry)

        # 3. Audience-specific strategy construction grounded in profile signals
        if audience_type == AudienceType.FAMILY:
            promise = "A heartwarming saga of heritage, resilience, and family unity across generations."
            creative_strategy = (
                "Focus on emotional warmth, father-son intergenerational craft, and collective victory. "
                "Strictly exclude all violence, sabotage, dark peril, and twist spoilers."
            )
            emotional_journey = matched_profile.tonal_priorities if matched_profile else ["curiosity", "warmth", "gentle tension", "triumph"]
            target_duration = 45.0 if not matched_profile else min(matched_profile.max_duration_seconds * 0.75, 45.0)
            target_rating = ContentRating.G
            candidate_scenes = ["scene_01", "scene_03", "scene_06", "scene_09"]
            excluded_scenes = ["scene_08", "scene_10", "scene_11"]
            preferred_music = "music_01_folk_acoustic"

        elif audience_type == AudienceType.YOUNG_ADULT:
            promise = "A high-stakes clash of ambition, rebellion, and industrial tech disruption."
            creative_strategy = (
                "Showcase fast-paced dialogue, electronic synth tempo, brother-sister teamwork, "
                "and corporate defiance. Do not reveal the secret investor or resolution."
            )
            emotional_journey = matched_profile.tonal_priorities if matched_profile else ["intrigue", "friction", "defiance", "anticipation"]
            target_duration = 38.0 if not matched_profile else min(matched_profile.max_duration_seconds * 0.85, 42.0)
            target_rating = ContentRating.PG_13
            candidate_scenes = ["scene_02", "scene_04", "scene_07", "scene_08"]
            excluded_scenes = ["scene_10", "scene_11"]
            preferred_music = "music_03_synth_pulse"

        elif audience_type == AudienceType.DIALECT_REGION:
            promise = "An authentic, deeply grounded portrayal of rural craftsmanship, local wit, and regional dignity."
            creative_strategy = (
                "Anchor in authentic colloquial dialogue, vernacular proverbs, and artisans' self-respect. "
                "Reject all comic caricatures, urban stereotyping, and spurious violence."
            )
            emotional_journey = matched_profile.tonal_priorities if matched_profile else ["cultural pride", "nostalgia", "respect", "collective resolve"]
            target_duration = 50.0 if not matched_profile else min(matched_profile.max_duration_seconds * 0.80, 50.0)
            target_rating = ContentRating.PG
            candidate_scenes = ["scene_01", "scene_05", "scene_06", "scene_09"]
            excluded_scenes = ["scene_08", "scene_10", "scene_11"]
            preferred_music = "music_01_folk_acoustic"

        else:
            raise ValueError(f"Unsupported audience type: {audience_type}")

        # Explicitly distinguish assumptions from evidence
        editorial_assumptions.extend([
            f"Assumed preferred music '{preferred_music}' best matches target emotional journey",
            f"Assumed {target_duration}s duration achieves optimal promotional retention for {audience_type.value}"
        ])

        brief = AudienceStrategyBrief(
            audience_type=audience_type,
            promise=promise,
            creative_strategy=creative_strategy,
            emotional_journey=emotional_journey,
            target_duration=target_duration,
            target_rating=target_rating,
            candidate_scenes=candidate_scenes,
            excluded_scenes=excluded_scenes,
            preferred_music=preferred_music,
            bias_warnings=bias_warnings,
            profile_signals=profile_signals,
            historical_hypotheses=historical_hypotheses,
            audience_evidence=audience_evidence,
            editorial_assumptions=editorial_assumptions
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="AudienceStrategyAgent",
                action="DEVELOP_STRATEGY",
                reason=f"Formulated strategy for {audience_type.value} consuming {len(profile_signals)} profile signals and testing {len(historical_hypotheses)} hypotheses",
                input_evidence=[
                    f"audience:{audience_type.value}",
                    f"profile_signals:{list(profile_signals.keys())}",
                    f"rating:{target_rating.value}"
                ],
                selected_decision={
                    "promise": promise,
                    "target_rating": target_rating.value,
                    "target_duration": target_duration,
                    "candidate_scenes": candidate_scenes,
                    "profile_signals_used": list(profile_signals.keys()),
                    "hypotheses_confirmed": [h["scene_id"] for h in historical_hypotheses if h["status"] == "CONFIRMED"],
                    "hypotheses_rejected": [h["scene_id"] for h in historical_hypotheses if h["status"] == "REJECTED"]
                },
                risk="LOW" if not bias_warnings else "MEDIUM"
            )

        return brief
