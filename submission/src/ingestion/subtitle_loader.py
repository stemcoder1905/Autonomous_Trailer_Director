"""Subtitle loader and alignment validation."""
from typing import List, Dict, Optional
from src.models.schemas import SubtitleItem, DialogueItem
from src.utils.timecode import timecode_to_seconds


class SubtitleLoader:
    """Loads and verifies subtitle items against source dialogues."""

    @staticmethod
    def verify_alignment(
        subtitles: List[SubtitleItem],
        dialogues: List[DialogueItem]
    ) -> List[Dict[str, str]]:
        """Verify that every subtitle maps to an existing dialogue and matches timing bounds."""
        dialogue_map = {d.dialogue_id: d for d in dialogues}
        discrepancies = []

        for sub in subtitles:
            if sub.source_dialogue_id not in dialogue_map:
                discrepancies.append({
                    "subtitle_id": sub.subtitle_id,
                    "error": f"Orphan subtitle referencing non-existent dialogue '{sub.source_dialogue_id}'"
                })
                continue

            parent_dial = dialogue_map[sub.source_dialogue_id]
            sub_in = timecode_to_seconds(sub.timestamp_in)
            sub_out = timecode_to_seconds(sub.timestamp_out)
            dial_in = timecode_to_seconds(parent_dial.timestamp_in)
            dial_out = timecode_to_seconds(parent_dial.timestamp_out)

            # Check if subtitle is roughly aligned within 1.0s tolerance
            if sub_in < dial_in - 1.0 or sub_out > dial_out + 1.0:
                discrepancies.append({
                    "subtitle_id": sub.subtitle_id,
                    "error": f"Subtitle timing ({sub.timestamp_in}-{sub.timestamp_out}) "
                             f"misaligned with dialogue ({parent_dial.timestamp_in}-{parent_dial.timestamp_out})"
                })

        return discrepancies
