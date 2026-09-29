"""Typed state definition for the Autonomous Trailer Director graph workflow."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from src.models.enums import AudienceType
from src.models.schemas import (
    EpisodePackage,
    StoryMap,
    ConstraintMap,
    TrailerPlan,
    TrailerValidationReport,
    ChangeImpactReport,
)


class DirectorState(BaseModel):
    """Immutable, typed state container passed through the agentic graph."""
    episode_package: Optional[EpisodePackage] = None
    story_map: Optional[StoryMap] = None
    constraint_map: Optional[ConstraintMap] = None
    trailer_plans: Dict[str, TrailerPlan] = Field(default_factory=dict)
    validation_reports: Dict[str, TrailerValidationReport] = Field(default_factory=dict)
    change_impact_reports: List[ChangeImpactReport] = Field(default_factory=list)
    active_scenario: Optional[str] = None
    current_node: str = "INITIALIZED"
    execution_history: List[str] = Field(default_factory=list)
    total_cost_usd: float = 0.0
