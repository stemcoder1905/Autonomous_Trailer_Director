"""Episode and metadata package loader."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.models.schemas import (
    EpisodePackage,
    SceneMetadata,
    DialogueItem,
    SubtitleItem,
    Character,
    Relationship,
    ConstraintRule,
    AudienceProfile,
    HistoricalPerformanceItem,
    CostSheet,
)
from src.utils.logger import logger


class EpisodePackageLoader:
    """Loads and validates all components of an episode package from disk."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def load_package(self, episode_file: Optional[Path] = None) -> EpisodePackage:
        """Load complete episode package including policies, contracts, and audience data."""
        # Find episode JSON
        ep_path = episode_file
        if not ep_path:
            ep_candidates = list((self.base_dir / "episode_package").glob("*.json"))
            if not ep_candidates:
                ep_candidates = list(self.base_dir.glob("*.json"))
            if not ep_candidates:
                raise FileNotFoundError(f"No episode JSON found in {self.base_dir}")
            ep_path = ep_candidates[0]

        logger.info(f"Loading episode data from: {ep_path}")
        with open(ep_path, "r", encoding="utf-8") as f:
            ep_data = json.load(f)

        scenes = [SceneMetadata(**s) for s in ep_data.get("scenes", [])]
        dialogues = [DialogueItem(**d) for d in ep_data.get("dialogues", [])]
        subtitles = [SubtitleItem(**sub) for sub in ep_data.get("subtitles", [])]
        characters = [Character(**c) for c in ep_data.get("characters", [])]
        relationships = [Relationship(**r) for r in ep_data.get("relationships", [])]

        # Contracts
        contracts: List[ConstraintRule] = []
        contracts_file = self.base_dir / "contracts" / "contracts.json"
        if contracts_file.exists():
            with open(contracts_file, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                contracts = [ConstraintRule(**rule) for rule in c_data]
        elif "contracts" in ep_data:
            contracts = [ConstraintRule(**rule) for rule in ep_data["contracts"]]

        # Policies
        policies: Dict[str, Any] = {}
        rating_policy_file = self.base_dir / "policies" / "rating_policy.json"
        if rating_policy_file.exists():
            with open(rating_policy_file, "r", encoding="utf-8") as f:
                policies.update(json.load(f))
        
        accessibility_policy_file = self.base_dir / "policies" / "accessibility_policy.json"
        if accessibility_policy_file.exists():
            with open(accessibility_policy_file, "r", encoding="utf-8") as f:
                policies.update(json.load(f))

        # Audience Profiles
        audience_profiles: List[AudienceProfile] = []
        audience_file = self.base_dir / "audience" / "audience_profiles.json"
        if audience_file.exists():
            with open(audience_file, "r", encoding="utf-8") as f:
                profiles_data = json.load(f)
                audience_profiles = [AudienceProfile(**p) for p in profiles_data]

        # Historical Performance
        historical: List[HistoricalPerformanceItem] = []
        hist_file = self.base_dir / "audience" / "historical_performance.json"
        if hist_file.exists():
            with open(hist_file, "r", encoding="utf-8") as f:
                h_data = json.load(f)
                historical = [HistoricalPerformanceItem(**item) for item in h_data]

        # Cost Sheet
        cost_sheet = CostSheet()
        costs_file = self.base_dir / "costs" / "cost_sheet.json"
        if costs_file.exists():
            with open(costs_file, "r", encoding="utf-8") as f:
                cost_sheet = CostSheet(**json.load(f))

        return EpisodePackage(
            episode_id=ep_data.get("episode_id", "unknown"),
            title=ep_data.get("title", "Untitled Episode"),
            duration_timecode=ep_data.get("duration_timecode", "00:00:00.000"),
            scenes=scenes,
            dialogues=dialogues,
            subtitles=subtitles,
            characters=characters,
            relationships=relationships,
            contracts=contracts,
            policies=policies,
            audience_profiles=audience_profiles,
            historical_performance=historical,
            cost_sheet=cost_sheet,
        )
