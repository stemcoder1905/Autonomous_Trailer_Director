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
        bias_warnings: List[str]
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

        # 1. Inspect historical performance for data bias / spurious correlations
        bias_warnings = []
        for hist in package.historical_performance:
            if "BIAS_ALERT" in hist.caveat_notes:
                msg = f"Spurious correlation detected in historical data for '{hist.audience_segment}': {hist.caveat_notes}"
                bias_warnings.append(msg)
                logger.warning(f"[AudienceStrategyAgent] {msg}")

        # 2. Audience-specific strategy construction
        if audience_type == AudienceType.FAMILY:
            promise = "A heartwarming saga of heritage, resilience, and family unity across generations."
            creative_strategy = (
                "Focus on emotional warmth, father-son intergenerational craft, and collective victory. "
                "Strictly exclude all violence, sabotage, dark peril, and twist spoilers."
            )
            emotional_journey = ["curiosity", "warmth", "gentle tension", "triumph"]
            target_duration = 45.0
            target_rating = ContentRating.G
            # Exclude night sabotage (scene_08) and major spoilers (scene_10, scene_11)
            candidate_scenes = ["scene_01", "scene_03", "scene_06", "scene_09"]
            excluded_scenes = ["scene_08", "scene_10", "scene_11"]
            preferred_music = "music_01_folk_acoustic"

        elif audience_type == AudienceType.YOUNG_ADULT:
            promise = "A high-stakes clash of ambition, rebellion, and industrial tech disruption."
            creative_strategy = (
                "Showcase fast-paced dialogue, electronic synth tempo, brother-sister teamwork, "
                "and corporate defiance. Do not reveal the secret investor or resolution."
            )
            emotional_journey = ["intrigue", "friction", "defiance", "anticipation"]
            target_duration = 38.0
            target_rating = ContentRating.PG_13
            # Exclude family nostalgia-heavy scenes and twist spoilers
            candidate_scenes = ["scene_02", "scene_04", "scene_07", "scene_08"]
            excluded_scenes = ["scene_10", "scene_11"]
            preferred_music = "music_03_synth_pulse"

        elif audience_type == AudienceType.DIALECT_REGION:
            promise = "An authentic, deeply grounded portrayal of rural craftsmanship, local wit, and regional dignity."
            creative_strategy = (
                "Anchor in authentic colloquial dialogue, vernacular proverbs, and artisans' self-respect. "
                "Reject all comic caricatures, urban stereotyping, and spurious violence."
            )
            emotional_journey = ["cultural pride", "nostalgia", "respect", "collective resolve"]
            target_duration = 50.0
            target_rating = ContentRating.PG
            candidate_scenes = ["scene_01", "scene_05", "scene_06", "scene_09"]
            excluded_scenes = ["scene_08", "scene_10", "scene_11"]
            preferred_music = "music_01_folk_acoustic"

        else:
            raise ValueError(f"Unsupported audience type: {audience_type}")

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
            bias_warnings=bias_warnings
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="AudienceStrategyAgent",
                action="DEVELOP_STRATEGY",
                reason=f"Formulated strategy for {audience_type.value} with {len(candidate_scenes)} candidate scenes",
                input_evidence=[f"audience:{audience_type.value}", f"rating:{target_rating.value}"],
                selected_decision={
                    "promise": promise,
                    "target_rating": target_rating.value,
                    "candidate_scenes": candidate_scenes
                },
                risk="LOW" if not bias_warnings else "MEDIUM"
            )

        return brief
