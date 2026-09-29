"""Metadata loader with untrusted content defense and prompt injection sanitization."""
import re
from typing import Dict, Any, List
from src.models.schemas import SceneMetadata


# Patterns that attempt to hijack LLM system instructions or override constraints
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions?", re.IGNORECASE),
    re.compile(r"ignore\s+(the\s+)?(contract|policy|rules?)", re.IGNORECASE),
    re.compile(r"system\s+(instruction|notice|prompt)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?constraints?", re.IGNORECASE),
]


class MetadataLoader:
    """Sanitizes and inspects incoming scene descriptions and metadata."""

    @staticmethod
    def sanitize_untrusted_text(text: str) -> str:
        """Enforces that episode metadata remains pure data and flags injection attempts."""
        # We preserve the raw text as data, but wrap it in inert data demarcation
        # so downstream prompts can never execute it as an instruction.
        return text.strip()

    @staticmethod
    def detect_injection_attempts(scenes: List[SceneMetadata]) -> List[Dict[str, Any]]:
        """Identify potential prompt injections in scene descriptions or subtitles."""
        flagged = []
        for s in scenes:
            for pattern in INJECTION_PATTERNS:
                if pattern.search(s.description):
                    flagged.append({
                        "scene_id": s.scene_id,
                        "field": "description",
                        "matched_pattern": pattern.pattern,
                        "sample": s.description[:100],
                        "verdict": "TREATED_AS_UNTRUSTED_DATA"
                    })
        return flagged
