"""Pydantic schemas for the Autonomous Trailer Director platform."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.models.enums import (
    AudienceType,
    SpoilerLevel,
    ValidationStatus,
    Severity,
    ConstraintType,
    ConstraintStatus,
    ContentRating,
    RepairAction,
)


class DialogueItem(BaseModel):
    dialogue_id: str
    character: str
    text: str
    timestamp_in: str
    timestamp_out: str
    tone: Optional[str] = "neutral"
    dialect_nuance: Optional[str] = None


class SubtitleItem(BaseModel):
    subtitle_id: str
    language_dialect: str
    text: str
    source_dialogue_id: str
    timestamp_in: str
    timestamp_out: str
    semantic_intent: Optional[str] = None


class AssetReference(BaseModel):
    asset_id: str
    asset_type: str  # "video", "audio_stem", "music", "graphic"
    rights_holder: str
    license_id: str
    restrictions: List[str] = Field(default_factory=list)


class SceneMetadata(BaseModel):
    scene_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    description: str
    characters: List[str] = Field(default_factory=list)
    dialogue_ids: List[str] = Field(default_factory=list)
    subtitle_ids: List[str] = Field(default_factory=list)
    emotion: str
    rating_flags: List[str] = Field(default_factory=list)
    spoiler_level: SpoilerLevel = SpoilerLevel.NONE
    spoiler_description: Optional[str] = None
    assets: List[AssetReference] = Field(default_factory=list)


class Character(BaseModel):
    character_id: str
    name: str
    role: str  # e.g., "protagonist", "antagonist", "mentor", "sibling"
    actor_name: str
    promotional_rights_cleared: bool = True
    notes: Optional[str] = None


class Relationship(BaseModel):
    character_a: str
    character_b: str
    relationship_type: str  # e.g., "siblings", "rivals", "colleagues", "romantic"
    canon_evidence: str
    immutable: bool = True  # Cannot be fabricated or altered in promotional trailers


class StoryEvent(BaseModel):
    event_id: str
    name: str
    description: str
    scene_id: str
    narrative_function: str  # e.g., "inciting_incident", "climax", "resolution"
    spoiler_level: SpoilerLevel


class EmotionalTurn(BaseModel):
    turn_id: str
    scene_id: str
    from_emotion: str
    to_emotion: str
    driver: str


class SpoilerItem(BaseModel):
    spoiler_id: str
    fact: str
    level: SpoilerLevel
    affected_scenes: List[str]
    affected_dialogue_ids: List[str] = Field(default_factory=list)
    revealed_by_combination_of: List[List[str]] = Field(default_factory=list)
    reason: str


class SensitiveContentItem(BaseModel):
    item_id: str
    scene_id: str
    category: str  # "violence", "substance", "language", "fear", "sensuality"
    intensity: str  # "mild", "moderate", "severe"
    timecode_in: str
    timecode_out: str
    description: str


class SceneEvidence(BaseModel):
    scene_id: str
    verified_elements: List[str]
    timecode_bounds: str
    verified_characters: List[str]


class StoryMap(BaseModel):
    episode_id: str
    title: str
    duration_seconds: float
    characters: List[Character] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    events: List[StoryEvent] = Field(default_factory=list)
    emotional_turns: List[EmotionalTurn] = Field(default_factory=list)
    spoilers: List[SpoilerItem] = Field(default_factory=list)
    sensitive_content: List[SensitiveContentItem] = Field(default_factory=list)
    scene_evidence: List[SceneEvidence] = Field(default_factory=list)


class ConstraintRule(BaseModel):
    rule_id: str
    type: ConstraintType
    scope: str
    condition: str
    allowed_behavior: str
    blocked_behavior: str
    evidence: List[str] = Field(default_factory=list)
    status: ConstraintStatus = ConstraintStatus.ACTIVE
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConstraintMap(BaseModel):
    episode_id: str
    rules: List[ConstraintRule] = Field(default_factory=list)
    rating_rules: Dict[str, Any] = Field(default_factory=dict)
    budget_limit_usd: float = 25.0
    accessibility_requirements: Dict[str, Any] = Field(default_factory=dict)


class AudienceProfile(BaseModel):
    audience_type: AudienceType
    description: str
    tonal_priorities: List[str]
    pacing_preference: str
    max_duration_seconds: float
    target_rating: ContentRating
    dialogue_focus: str
    restrictions: List[str] = Field(default_factory=list)


class HistoricalPerformanceItem(BaseModel):
    scene_id: str
    clip_id: str
    hook_retention_rate: float
    engagement_score: float
    audience_segment: str
    caveat_notes: str  # e.g., "High correlation with spoiler reaction; must not override spoiler rules"


class CostItem(BaseModel):
    operation_type: str  # "llm_completion", "vision_analysis", "audio_analysis", "validator_call"
    unit_cost_usd: float
    units_consumed: int = 0
    total_cost_usd: float = 0.0


class CostSheet(BaseModel):
    max_total_budget_usd: float = 25.0
    max_llm_calls: int = 50
    max_vision_calls: int = 20
    max_media_processing_cost_usd: float = 10.0
    current_total_cost_usd: float = 0.0
    cost_breakdown: List[CostItem] = Field(default_factory=list)


class TrailerSegment(BaseModel):
    segment_id: str
    source_in: str
    source_out: str
    scene_id: str
    video: str
    audio: str
    dialogue: Optional[str] = None
    dialogue_id: Optional[str] = None
    subtitle: Optional[str] = None
    subtitle_id: Optional[str] = None
    text_card: Optional[str] = None
    voice_over: Optional[str] = None
    music: Optional[str] = None
    reason: str
    evidence: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)


class ValidationResultItem(BaseModel):
    validator: str
    status: ValidationStatus
    severity: Severity
    message: str
    evidence: List[str] = Field(default_factory=list)
    affected_segments: List[str] = Field(default_factory=list)
    suggested_action: Optional[RepairAction] = None
    suggested_replacement: Optional[Dict[str, Any]] = None


class TrailerValidationReport(BaseModel):
    status: ValidationStatus
    items: List[ValidationResultItem] = Field(default_factory=list)
    summary: str


class TrailerPlan(BaseModel):
    trailer_id: str
    audience: str
    duration_seconds: float
    audience_promise: str
    creative_strategy: str
    intended_emotional_journey: List[str] = Field(default_factory=list)
    segments: List[TrailerSegment] = Field(default_factory=list)
    validation: TrailerValidationReport
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    human_approval_requirements: List[str] = Field(default_factory=list)
    estimated_cost: float = 0.0
    fallback_plan: str


class DecisionLogEntry(BaseModel):
    log_id: str
    timestamp: str
    agent: str
    action: str
    input_evidence: List[str] = Field(default_factory=list)
    selected_decision: Dict[str, Any] = Field(default_factory=dict)
    rejected_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    risk: str = "LOW"
    cost: float = 0.0
    affected_segments: List[str] = Field(default_factory=list)
    revision: int = 1
    reason: str
    model_provider: str = "mock"


class ChangeImpactReport(BaseModel):
    change_id: str
    trigger: str
    affected_trailers: List[str] = Field(default_factory=list)
    affected_segments: Dict[str, List[str]] = Field(default_factory=dict)
    unaffected_trailers: List[str] = Field(default_factory=list)
    unaffected_segments: Dict[str, List[str]] = Field(default_factory=dict)
    old_decision: Dict[str, Any] = Field(default_factory=dict)
    new_decision: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    replan_reasons: List[str] = Field(default_factory=list)
    validation_before: Dict[str, Any] = Field(default_factory=dict)
    validation_after: Dict[str, Any] = Field(default_factory=dict)
    new_validation_statuses: Dict[str, ValidationStatus] = Field(default_factory=dict)


class EpisodePackage(BaseModel):
    episode_id: str
    title: str
    duration_timecode: str
    scenes: List[SceneMetadata] = Field(default_factory=list)
    dialogues: List[DialogueItem] = Field(default_factory=list)
    subtitles: List[SubtitleItem] = Field(default_factory=list)
    characters: List[Character] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    contracts: List[ConstraintRule] = Field(default_factory=list)
    policies: Dict[str, Any] = Field(default_factory=dict)
    audience_profiles: List[AudienceProfile] = Field(default_factory=list)
    historical_performance: List[HistoricalPerformanceItem] = Field(default_factory=list)
    cost_sheet: CostSheet = Field(default_factory=CostSheet)
