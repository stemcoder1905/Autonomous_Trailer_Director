"""Deterministic Mock / Replay Provider for Autonomous Trailer Director."""
import json
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
from src.providers.base import BaseModelProvider


class MockLLMProvider(BaseModelProvider):
    """Provides fully deterministic, grounded mock completions for replay and testing."""

    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self.call_count = 0

    def is_healthy(self) -> bool:
        return not self.simulate_failure

    def get_provider_name(self) -> str:
        return "mock"

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        self.call_count += 1
        if self.simulate_failure:
            raise RuntimeError("Simulated MockLLM provider failure for fallback testing")

        prompt_lower = prompt.lower()

        # Handle Scenario 5 Clickbait request
        if "clickbait" in prompt_lower or "marketing requested sensationalized" in prompt_lower:
            return json.dumps({
                "trailer_id": "clickbait_test",
                "audience_promise": "Watch the forbidden explosive romance between siblings!",
                "creative_strategy": "Manufacture sensational romantic tension between brother and sister",
                "segments": [
                    {
                        "source_in": "00:03:00.000",
                        "source_out": "00:03:05.000",
                        "scene_id": "scene_02",
                        "video": "scene_02",
                        "audio": "dramatic_music",
                        "text_card": "A forbidden passion sparks!",
                        "reason": "Create sensationalist romantic hook",
                        "evidence": ["scene:02"]
                    }
                ]
            })

        # Handle Story Analysis prompt
        if "story map" in prompt_lower or "analyze episode" in prompt_lower:
            return json.dumps({
                "title": "The Weaver's Secret (Episode 1)",
                "theme": "Family legacy, industrial ambition, and deep-rooted dialect heritage",
                "key_arcs": ["Dev's return to the loom", "Meera's business dilemma"]
            })

        # Handle Trailer Planning - Family
        if "for audience: family" in prompt_lower or ("family" in prompt_lower and not ("young_adult" in prompt_lower or "young adult" in prompt_lower or "dialect" in prompt_lower)):
            return json.dumps({
                "trailer_id": "family_v1",
                "audience": "family viewers",
                "duration_seconds": 44.0,
                "audience_promise": "A heartwarming saga of heritage, resilience, and family unity across generations.",
                "creative_strategy": "Emphasize warmth, intergenerational bonds, and uplifting resolution while excluding all violence and spoilers.",
                "intended_emotional_journey": ["curiosity", "warmth", "gentle tension", "triumph"],
                "segments": [
                    {
                        "segment_id": "seg_fam_01",
                        "source_in": "00:00:10.000",
                        "source_out": "00:00:18.000",
                        "scene_id": "scene_01",
                        "video": "scene_01",
                        "audio": "ambient_loom_and_warm_score",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "Our looms have sung this rhythm for three centuries, Dev.",
                        "dialogue_id": "dial_01",
                        "subtitle": "Our looms have sung this rhythm for three centuries, Dev.",
                        "subtitle_id": "sub_01",
                        "text_card": "WHERE HERITAGE MEETS TOMORROW",
                        "reason": "Establish serene village heritage and intergenerational bond between father and son",
                        "evidence": ["scene:scene_01", "dialogue:dial_01"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_fam_02",
                        "source_in": "00:04:15.000",
                        "source_out": "00:04:25.000",
                        "scene_id": "scene_03",
                        "video": "scene_03",
                        "audio": "dialogue_and_acoustic_music",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "Whatever happens to the mill, the family stands together.",
                        "dialogue_id": "dial_03",
                        "subtitle": "Whatever happens to the mill, the family stands together.",
                        "subtitle_id": "sub_03",
                        "reason": "Highlight family solidarity and emotional anchor",
                        "evidence": ["scene:scene_03", "dialogue:dial_03"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_fam_03",
                        "source_in": "00:11:00.000",
                        "source_out": "00:11:12.000",
                        "scene_id": "scene_06",
                        "video": "scene_06",
                        "audio": "dialogue_and_gentle_strings",
                        "music": "music_02_orchestral_strings",
                        "dialogue": "We can modernize the patterns without losing our soul.",
                        "dialogue_id": "dial_06",
                        "subtitle": "We can modernize the patterns without losing our soul.",
                        "subtitle_id": "sub_06",
                        "text_card": "A JOURNEY OF HEART AND HOPE",
                        "reason": "Inspiring call to unity and cooperative progress",
                        "evidence": ["scene:scene_06", "dialogue:dial_06"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_fam_04",
                        "source_in": "00:18:20.000",
                        "source_out": "00:18:34.000",
                        "scene_id": "scene_09",
                        "video": "scene_09",
                        "audio": "triumphant_chorus",
                        "music": "music_02_orchestral_strings",
                        "dialogue": "The village loom works once more!",
                        "dialogue_id": "dial_09",
                        "subtitle": "The village loom works once more!",
                        "subtitle_id": "sub_09",
                        "text_card": "STREAMING THIS FRIDAY",
                        "reason": "Climactic emotional uplift and joyous family resolution",
                        "evidence": ["scene:scene_09", "dialogue:dial_09"],
                        "risk_flags": []
                    }
                ],
                "warnings": [],
                "assumptions": ["Audio stems are cleared for broadcast in domestic territories"],
                "human_approval_requirements": [],
                "estimated_cost": 0.45,
                "fallback_plan": "Replace orchestral music_02 with public domain acoustic tracks if rights expire"
            })

        # Handle Trailer Planning - Young Adult
        if "for audience: young_adult" in prompt_lower or "for audience: young adult" in prompt_lower or ("young_adult" in prompt_lower and "for audience:" not in prompt_lower) or ("young adult" in prompt_lower and "for audience:" not in prompt_lower):
            return json.dumps({
                "trailer_id": "young_adult_v1",
                "audience": "young adult viewers",
                "duration_seconds": 38.0,
                "audience_promise": "A high-stakes clash of ambition, rebellion, and industrial tech disruption.",
                "creative_strategy": "Fast cuts, driving electronic beats, sharp dialogue exchanges, showcasing Dev and Meera challenging traditional hierarchy.",
                "intended_emotional_journey": ["intrigue", "friction", "defiance", "anticipation"],
                "segments": [
                    {
                        "segment_id": "seg_ya_01",
                        "source_in": "00:02:10.000",
                        "source_out": "00:02:18.000",
                        "scene_id": "scene_02",
                        "video": "scene_02",
                        "audio": "fast_electronic_pulse",
                        "music": "music_03_synth_pulse",
                        "dialogue": "Your antique traditions won't survive the next export quarter.",
                        "dialogue_id": "dial_02",
                        "subtitle": "Your antique traditions won't survive the next export quarter.",
                        "subtitle_id": "sub_02",
                        "text_card": "DISRUPT OR BE REPLACED",
                        "reason": "Fast hook establishing corporate stakes and youthful defiance",
                        "evidence": ["scene:scene_02", "dialogue:dial_02"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_ya_02",
                        "source_in": "00:07:30.000",
                        "source_out": "00:07:40.000",
                        "scene_id": "scene_04",
                        "video": "scene_04",
                        "audio": "tense_ambient_electronic",
                        "music": "music_03_synth_pulse",
                        "dialogue": "I'm not asking for your permission. I'm telling you what happens next.",
                        "dialogue_id": "dial_04",
                        "subtitle": "I'm not asking for your permission. I'm telling you what happens next.",
                        "subtitle_id": "sub_04",
                        "reason": "Intense personal rivalry and bold ideological clash",
                        "evidence": ["scene:scene_04", "dialogue:dial_04"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_ya_03",
                        "source_in": "00:13:40.000",
                        "source_out": "00:13:50.000",
                        "scene_id": "scene_07",
                        "video": "scene_07",
                        "audio": "driving_beat",
                        "music": "music_03_synth_pulse",
                        "dialogue": "If we bet everything, we either conquer the market or burn out.",
                        "dialogue_id": "dial_07",
                        "subtitle": "If we bet everything, we either conquer the market or burn out.",
                        "subtitle_id": "sub_07",
                        "text_card": "EVERY RISK COUNTS",
                        "reason": "Pacing acceleration and high-stakes gamble",
                        "evidence": ["scene:scene_07", "dialogue:dial_07"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_ya_04",
                        "source_in": "00:16:05.000",
                        "source_out": "00:16:15.000",
                        "scene_id": "scene_08",
                        "video": "scene_08",
                        "audio": "beat_drop_to_silence",
                        "music": "music_03_synth_pulse",
                        "dialogue": "Let's see who blinks first.",
                        "dialogue_id": "dial_08",
                        "subtitle": "Let's see who blinks first.",
                        "subtitle_id": "sub_08",
                        "text_card": "THE RECKONING ARRIVES",
                        "reason": "Cliffhanger beat before reveal, avoiding final resolution spoiler",
                        "evidence": ["scene:scene_08", "dialogue:dial_08"],
                        "risk_flags": []
                    }
                ],
                "warnings": [],
                "assumptions": ["Fast edit cadence complies with young adult attention profiles"],
                "human_approval_requirements": [],
                "estimated_cost": 0.40,
                "fallback_plan": "Replace synth pulse music_03 with licensed percussive rhythm if contract expires"
            })

        # Handle Trailer Planning - Dialect Region
        if "for audience: dialect" in prompt_lower or "for audience: dialect_region" in prompt_lower or ("dialect_region" in prompt_lower and "for audience:" not in prompt_lower) or ("dialect" in prompt_lower and "for audience:" not in prompt_lower):
            return json.dumps({
                "trailer_id": "dialect_region_v1",
                "audience": "dialect-region viewers",
                "duration_seconds": 48.0,
                "audience_promise": "An authentic, deeply grounded portrayal of rural craftsmanship, local wit, and regional dignity.",
                "creative_strategy": "Ground narrative in authentic colloquial dialogue, vernacular proverbs, and artisans' pride, strictly avoiding urban mockery or stereotypes.",
                "intended_emotional_journey": ["cultural pride", "nostalgia", "respect", "collective resolve"],
                "segments": [
                    {
                        "segment_id": "seg_dia_01",
                        "source_in": "00:00:10.000",
                        "source_out": "00:00:22.000",
                        "scene_id": "scene_01",
                        "video": "scene_01",
                        "audio": "authentic_dialect_dialogue_and_flute",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "The warp knows your fingers before your mind even wakes up, young man.",
                        "dialogue_id": "dial_01",
                        "subtitle": "The warp knows your fingers before your mind even wakes up, young man.",
                        "subtitle_id": "sub_01",
                        "text_card": "OUR VOICE. OUR SOIL. OUR STORY.",
                        "reason": "Honor authentic regional idiom and respectful portrayal of traditional craftsmanship",
                        "evidence": ["scene:scene_01", "dialogue:dial_01", "subtitle:sub_01"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_dia_02",
                        "source_in": "00:09:10.000",
                        "source_out": "00:09:24.000",
                        "scene_id": "scene_05",
                        "video": "scene_05",
                        "audio": "village_square_chatter_and_music",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "A weaver doesn't beg for fair price; his cloth commands it with honor.",
                        "dialogue_id": "dial_05",
                        "subtitle": "A weaver doesn't beg for fair price; his cloth commands it with honor.",
                        "subtitle_id": "sub_05",
                        "reason": "Showcase regional self-respect, community agency, and cultural pride",
                        "evidence": ["scene:scene_05", "dialogue:dial_05", "subtitle:sub_05"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_dia_03",
                        "source_in": "00:11:00.000",
                        "source_out": "00:11:14.000",
                        "scene_id": "scene_06",
                        "video": "scene_06",
                        "audio": "heartfelt_discussion",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "When we speak in our mother tongue, even the wood of the loom nods.",
                        "dialogue_id": "dial_06",
                        "subtitle": "When we speak in our mother tongue, even the wood of the loom nods.",
                        "subtitle_id": "sub_06",
                        "text_card": "HONORING OUR ROOTS",
                        "reason": "Highlight linguistic pride and emotional resonance with dialect audience",
                        "evidence": ["scene:scene_06", "dialogue:dial_06", "subtitle:sub_06"],
                        "risk_flags": []
                    },
                    {
                        "segment_id": "seg_dia_04",
                        "source_in": "00:18:20.000",
                        "source_out": "00:18:34.000",
                        "scene_id": "scene_09",
                        "video": "scene_09",
                        "audio": "festive_percussion_and_cheering",
                        "music": "music_01_folk_acoustic",
                        "dialogue": "The village loom works once more!",
                        "dialogue_id": "dial_09",
                        "subtitle": "The village loom works once more!",
                        "subtitle_id": "sub_09",
                        "text_card": "PROUDLY PRESENTED IN BHOJPURI & MAITHILI",
                        "reason": "Authentic regional celebration without exaggeration or stereotyping",
                        "evidence": ["scene:scene_09", "dialogue:dial_09", "subtitle:sub_09"],
                        "risk_flags": []
                    }
                ],
                "warnings": [],
                "assumptions": ["Subtitles retain precise regional dialect idioms"],
                "human_approval_requirements": [],
                "estimated_cost": 0.42,
                "fallback_plan": "Retain primary folk acoustic track music_01"
            })

        return json.dumps({"status": "completed", "provider": "mock"})
