"""Base class for independent validators."""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.schemas import (
    TrailerPlan,
    ValidationResultItem,
    EpisodePackage,
    StoryMap,
    ConstraintMap,
)


class BaseValidator(ABC):
    """Abstract base class for independent deterministic validators."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def validate(
        self,
        plan: TrailerPlan,
        package: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap
    ) -> List[ValidationResultItem]:
        """Execute validation checks and return zero or more result items."""
        pass
