"""Enumerations for the Autonomous Trailer Director platform."""
from enum import Enum


class AudienceType(str, Enum):
    FAMILY = "family"
    YOUNG_ADULT = "young_adult"
    DIALECT_REGION = "dialect_region"


class SpoilerLevel(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConstraintType(str, Enum):
    ACTOR_RESTRICTION = "actor_restriction"
    TERRITORY_RESTRICTION = "territory_restriction"
    MUSIC_RESTRICTION = "music_restriction"
    AGE_RATING = "age_rating"
    SCENE_RESTRICTION = "scene_restriction"
    SUBTITLE_RESTRICTION = "subtitle_restriction"
    ACCESSIBILITY = "accessibility"
    BUDGET = "budget"


class ConstraintStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"


class ContentRating(str, Enum):
    G = "G"
    PG = "PG"
    PG_13 = "PG-13"
    R = "R"
    TV_MA = "TV-MA"


class RepairAction(str, Enum):
    REPLACE_SEGMENT = "REPLACE_SEGMENT"
    ADJUST_TIMECODE = "ADJUST_TIMECODE"
    REMOVE_DIALOGUE = "REMOVE_DIALOGUE"
    CHANGE_SUBTITLE = "CHANGE_SUBTITLE"
    CHANGE_MUSIC = "CHANGE_MUSIC"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
