"""Configuration module for Autonomous Trailer Director."""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class SystemConfig(BaseModel):
    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    sample_data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "sample_data")
    sample_run_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "sample_run")
    
    # Model Provider Settings
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    llm_api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    
    # Cost & Guardrails
    max_llm_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_LLM_CALLS", "50")))
    max_vision_calls: int = Field(default_factory=lambda: int(os.getenv("MAX_VISION_CALLS", "20")))
    max_media_processing_cost_usd: float = Field(
        default_factory=lambda: float(os.getenv("MAX_MEDIA_PROCESSING_COST", "10.0"))
    )
    max_total_cost_usd: float = Field(default_factory=lambda: float(os.getenv("MAX_TOTAL_COST", "25.0")))
    
    # Unit costs for budget tracking
    unit_cost_llm_call: float = 0.05
    unit_cost_vision_call: float = 0.10
    unit_cost_audio_call: float = 0.05
    unit_cost_validator_call: float = 0.005

    # Trailer duration constraints (seconds)
    family_duration_target: float = 45.0
    family_duration_max: float = 60.0
    young_adult_duration_target: float = 35.0
    young_adult_duration_max: float = 45.0
    dialect_duration_target: float = 50.0
    dialect_duration_max: float = 65.0


def get_config() -> SystemConfig:
    return SystemConfig()
