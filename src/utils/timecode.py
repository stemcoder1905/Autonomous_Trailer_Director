"""Timecode utility functions for video EDL processing."""
import re
from typing import Tuple


TIMECODE_REGEX = re.compile(r"^(\d{2}):(\d{2}):(\d{2})(?:[.:](\d{2,3}))?$")


def is_valid_timecode(tc: str) -> bool:
    """Check if the string matches HH:MM:SS.mmm format."""
    if not isinstance(tc, str):
        return False
    return bool(TIMECODE_REGEX.match(tc.strip()))


def timecode_to_seconds(tc: str) -> float:
    """Convert timecode string 'HH:MM:SS.mmm' or 'HH:MM:SS' to total seconds."""
    match = TIMECODE_REGEX.match(tc.strip())
    if not match:
        raise ValueError(f"Invalid timecode format: '{tc}'. Expected HH:MM:SS.mmm")
    
    hours, minutes, seconds, fraction = match.groups()
    total = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    if fraction:
        # Standardize 2-digit (frames/centiseconds) or 3-digit (milliseconds)
        if len(fraction) == 2:
            total += int(fraction) / 100.0
        else:
            total += int(fraction) / 1000.0
    return round(total, 3)


def seconds_to_timecode(sec: float) -> str:
    """Convert total seconds to timecode string 'HH:MM:SS.mmm'."""
    if sec < 0:
        raise ValueError(f"Negative seconds cannot be converted to timecode: {sec}")
    
    hours = int(sec // 3600)
    remainder = sec % 3600
    minutes = int(remainder // 60)
    seconds = int(remainder % 60)
    millis = int(round((remainder % 1) * 1000))
    if millis >= 1000:
        seconds += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def is_valid_segment_span(source_in: str, source_out: str) -> Tuple[bool, str]:
    """Validate that source_in < source_out and both timecodes are valid."""
    if not is_valid_timecode(source_in):
        return False, f"Invalid source_in timecode: '{source_in}'"
    if not is_valid_timecode(source_out):
        return False, f"Invalid source_out timecode: '{source_out}'"
    
    in_sec = timecode_to_seconds(source_in)
    out_sec = timecode_to_seconds(source_out)
    if in_sec >= out_sec:
        return False, f"source_in ({source_in}, {in_sec}s) must be strictly before source_out ({source_out}, {out_sec}s)"
    return True, ""


def is_within_bounds(source_in: str, source_out: str, scene_start: str, scene_end: str) -> Tuple[bool, str]:
    """Validate that source_in and source_out lie strictly within scene bounds."""
    valid_span, msg = is_valid_segment_span(source_in, source_out)
    if not valid_span:
        return False, msg
    
    in_sec = timecode_to_seconds(source_in)
    out_sec = timecode_to_seconds(source_out)
    start_sec = timecode_to_seconds(scene_start)
    end_sec = timecode_to_seconds(scene_end)
    
    if in_sec < start_sec:
        return False, f"source_in ({source_in}) is before scene start ({scene_start})"
    if out_sec > end_sec:
        return False, f"source_out ({source_out}) exceeds scene end ({scene_end})"
    return True, ""
