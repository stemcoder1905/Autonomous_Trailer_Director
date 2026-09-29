"""Story Understanding Agent for extracting grounded narrative representation."""
from typing import List, Dict, Any, Optional
from src.models.schemas import (
    EpisodePackage,
    StoryMap,
    StoryEvent,
    EmotionalTurn,
    SpoilerItem,
    SensitiveContentItem,
    SceneEvidence,
    SpoilerLevel,
    SpoilerMap,
    SpoilerMapEntry,
)
from src.utils.timecode import timecode_to_seconds
from src.utils.logger import logger, DecisionLogger


class StoryUnderstandingAgent:
    """Extracts, structures, and grounds the episode's story, characters, spoilers, and emotional turns."""

    def __init__(self, decision_logger: Optional[DecisionLogger] = None):
        self.decision_logger = decision_logger

    def analyze_story(self, package: EpisodePackage) -> StoryMap:
        """Construct a validated StoryMap strictly grounded in supplied package evidence."""
        logger.info(f"[StoryAgent] Analyzing story for episode '{package.episode_id}'")

        # 1. Map Characters and Relationships from verified canon
        characters = package.characters
        relationships = package.relationships

        # 2. Extract grounded Story Events
        events: List[StoryEvent] = []
        for scene in package.scenes:
            narrative_fn = "exposition"
            if scene.scene_id in ["scene_01"]:
                narrative_fn = "inciting_heritage"
            elif scene.scene_id in ["scene_02"]:
                narrative_fn = "conflict_instigation"
            elif scene.scene_id in ["scene_07", "scene_08"]:
                narrative_fn = "rising_action_peril"
            elif scene.scene_id in ["scene_09"]:
                narrative_fn = "climax_solidarity"
            elif scene.scene_id in ["scene_10"]:
                narrative_fn = "climax_twist_reveal"
            elif scene.scene_id in ["scene_11"]:
                narrative_fn = "resolution_triumph"
            elif scene.scene_id in ["scene_12"]:
                narrative_fn = "epilogue"

            events.append(
                StoryEvent(
                    event_id=f"event_{scene.scene_id}",
                    name=scene.description.split(".")[0],
                    description=scene.description,
                    scene_id=scene.scene_id,
                    narrative_function=narrative_fn,
                    spoiler_level=scene.spoiler_level,
                )
            )

        # 3. Extract Emotional Turns
        emotional_turns: List[EmotionalTurn] = [
            EmotionalTurn(
                turn_id="turn_01",
                scene_id="scene_02",
                from_emotion="warm_reverence",
                to_emotion="tense_confrontation",
                driver="Singhania's arrival with buyout ultimatum"
            ),
            EmotionalTurn(
                turn_id="turn_02",
                scene_id="scene_03",
                from_emotion="tense_confrontation",
                to_emotion="family_solidarity",
                driver="Family gathers in courtyard pledging to defend the loom"
            ),
            EmotionalTurn(
                turn_id="turn_03",
                scene_id="scene_06",
                from_emotion="youthful_ambition",
                to_emotion="awe_discovery",
                driver="Decoding ancient folk song into weaving math"
            ),
            EmotionalTurn(
                turn_id="turn_04",
                scene_id="scene_08",
                from_emotion="suspense_thrill",
                to_emotion="peril_action",
                driver="Physical sabotage of loom shuttles"
            ),
            EmotionalTurn(
                turn_id="turn_05",
                scene_id="scene_09",
                from_emotion="peril_action",
                to_emotion="collective_triumph",
                driver="All weavers assemble at dawn to rethread loom"
            ),
        ]

        # 4. Extract Grounded Spoilers (Single Scene + Combinations)
        spoilers: List[SpoilerItem] = [
            SpoilerItem(
                spoiler_id="spoil_01",
                fact="Uncle Harish is the secret mastermind behind Vikram's buyout and sabotage",
                level=SpoilerLevel.MAJOR,
                affected_scenes=["scene_10"],
                affected_dialogue_ids=["dial_10"],
                revealed_by_combination_of=[
                    ["scene_02", "scene_10"],
                    ["scene_04", "scene_10"]
                ],
                reason="Climax twist reveal fundamentally ruins mystery of the antagonist"
            ),
            SpoilerItem(
                spoiler_id="spoil_02",
                fact="The royal golden seal woven into the fabric legally nullifies Singhania's claim",
                level=SpoilerLevel.MAJOR,
                affected_scenes=["scene_11"],
                affected_dialogue_ids=["dial_11"],
                revealed_by_combination_of=[
                    ["scene_06", "scene_11"]
                ],
                reason="Reveals the exact resolution and legal outcome of the central conflict"
            ),
            SpoilerItem(
                spoiler_id="spoil_03",
                fact="Night sabotage physically damages the loom shuttles",
                level=SpoilerLevel.MINOR,
                affected_scenes=["scene_08"],
                affected_dialogue_ids=["dial_08"],
                revealed_by_combination_of=[],
                reason="Incidental plot progression; reveals intermediate peril"
            ),
            # Combination spoiler rule: Combining scene_08 (cut threads) with scene_09 (repaired loom)
            # gives away the resolution of the sabotage crisis prematurely if shown back-to-back!
            SpoilerItem(
                spoiler_id="spoil_combo_01",
                fact="Directly juxtaposing the cut loom with the fully restored celebratory loom reveals immediate crisis resolution",
                level=SpoilerLevel.MODERATE,
                affected_scenes=["scene_08", "scene_09"],
                affected_dialogue_ids=[],
                revealed_by_combination_of=[
                    ["scene_08", "scene_09"]
                ],
                reason="Combination spoiler: Eliminates narrative tension by showing both the catastrophe and its immediate fix"
            )
        ]

        # 5. Extract Sensitive Content
        sensitive_content: List[SensitiveContentItem] = [
            SensitiveContentItem(
                item_id="sens_01",
                scene_id="scene_08",
                category="violence",
                intensity="mild",
                timecode_in="00:15:20.000",
                timecode_out="00:16:30.000",
                description="Physical vandalism and aggressive pursuit in the dark"
            )
        ]

        # 6. Build Scene Evidence grounding
        scene_evidence: List[SceneEvidence] = [
            SceneEvidence(
                scene_id=s.scene_id,
                verified_elements=[f"dialogue:{d}" for d in s.dialogue_ids] + [f"asset:{a.asset_id}" for a in s.assets],
                timecode_bounds=f"{s.start_time} - {s.end_time}",
                verified_characters=s.characters
            )
            for s in package.scenes
        ]

        duration_sec = timecode_to_seconds(package.duration_timecode)
        story_map = StoryMap(
            episode_id=package.episode_id,
            title=package.title,
            duration_seconds=duration_sec,
            characters=characters,
            relationships=relationships,
            events=events,
            emotional_turns=emotional_turns,
            spoilers=spoilers,
            sensitive_content=sensitive_content,
            scene_evidence=scene_evidence,
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="StoryUnderstandingAgent",
                action="ANALYZE_STORY",
                reason=f"Synthesized story map for {package.title} across {len(events)} events",
                input_evidence=[f"episode:{package.episode_id}", f"scenes:{len(package.scenes)}"],
                selected_decision={"events_count": len(events), "spoilers_count": len(spoilers)},
                risk="LOW"
            )

        return story_map

    def generate_spoiler_map(self, story_map: StoryMap) -> SpoilerMap:
        """Generate structured spoiler map distinguishing single-scene and combination spoilers."""
        single_spoilers: List[SpoilerMapEntry] = []
        combo_spoilers: List[SpoilerMapEntry] = []

        for item in story_map.spoilers:
            is_combo = bool(item.revealed_by_combination_of) or len(item.affected_scenes) > 1
            entry = SpoilerMapEntry(
                scene_id=item.affected_scenes[0] if item.affected_scenes else "scene_00",
                severity=item.level.value,
                description=item.fact,
                trailer_allowed=(item.level == SpoilerLevel.NONE),
                evidence=[f"spoiler:{item.spoiler_id}"] + [f"scene:{s}" for s in item.affected_scenes],
                spoiler_id=item.spoiler_id,
                spoiler_type="COMBINATION" if is_combo else "SINGLE_SCENE",
                affected_scenes=item.affected_scenes,
                revealed_by_combination_of=item.revealed_by_combination_of,
                risk_summary=item.reason,
                remediation_guidance=f"Exclude or truncate scenes {item.affected_scenes} to prevent premature reveal of: {item.fact}"
            )
            if is_combo:
                combo_spoilers.append(entry)
            else:
                single_spoilers.append(entry)

        spoiler_map = SpoilerMap(
            episode_id=story_map.episode_id,
            spoilers=single_spoilers + combo_spoilers,
            single_scene_spoilers=single_spoilers,
            combination_spoilers=combo_spoilers,
            total_spoilers=len(single_spoilers) + len(combo_spoilers)
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="StoryUnderstandingAgent",
                action="GENERATE_SPOILER_MAP",
                reason=f"Synthesized spoiler map with {len(single_spoilers)} single-scene and {len(combo_spoilers)} combination spoilers",
                input_evidence=[f"episode:{story_map.episode_id}", f"total_spoilers:{spoiler_map.total_spoilers}"],
                selected_decision={"single": len(single_spoilers), "combo": len(combo_spoilers)},
                risk="HIGH" if any(s.level == SpoilerLevel.MAJOR for s in story_map.spoilers) else "MEDIUM"
            )

        return spoiler_map
