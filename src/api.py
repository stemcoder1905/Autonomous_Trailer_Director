"""FastAPI Web Service for Autonomous Trailer Director."""
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import AudienceType, ConstraintStatus
from src.models.schemas import (
    EpisodePackage,
    StoryMap,
    ConstraintMap,
    TrailerPlan,
    TrailerValidationReport,
    ChangeImpactReport,
    ConstraintRule,
)
from src.providers.llm import ProviderManager
from src.utils.logger import DecisionLogger
from src.config import get_config


app = FastAPI(
    title="Autonomous Trailer Director API",
    description="Agentic editorial planning and independent verification platform for OTT dialect streaming.",
    version="1.0.0"
)

config = get_config()


class RunRequest(BaseModel):
    input_path: Optional[str] = "sample_data"
    audience: Optional[str] = "all"
    scenario: Optional[str] = "none"


class PlanRequest(BaseModel):
    input_path: Optional[str] = "sample_data"
    audience: str = "family"


class ValidateRequest(BaseModel):
    plan: TrailerPlan
    input_path: Optional[str] = "sample_data"


class ReplanRequest(BaseModel):
    rule_id: str
    scope: str
    status: str
    expiry_date: Optional[str] = None
    input_path: Optional[str] = "sample_data"


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Autonomous Trailer Director",
        "version": "1.0.0",
        "active_provider": config.llm_provider
    }


@app.post("/analyze")
def analyze_episode(request: RunRequest):
    input_dir = Path(request.input_path)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")
    
    workflow = TrailerDirectorWorkflow(base_dir=input_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)
    return {
        "story_map": story_map.model_dump(),
        "constraint_map": constraint_map.model_dump()
    }


@app.post("/plan")
def plan_trailer(request: PlanRequest):
    input_dir = Path(request.input_path)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")

    aud_type = AudienceType(request.audience)
    workflow = TrailerDirectorWorkflow(base_dir=input_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)
    brief = workflow.audience_agent.create_strategy(aud_type, pkg, story_map, constraint_map)
    plan = workflow.planner_agent.plan_trailer(brief, pkg, story_map, constraint_map)
    return plan.model_dump()


@app.post("/validate")
def validate_trailer(request: ValidateRequest):
    input_dir = Path(request.input_path)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")

    workflow = TrailerDirectorWorkflow(base_dir=input_dir)
    pkg = workflow.loader.load_package()
    story_map = workflow.story_agent.analyze_story(pkg)
    constraint_map = workflow.constraint_agent.analyze_constraints(pkg)
    report = workflow.validator_agent.validate_plan(request.plan, pkg, story_map, constraint_map)
    return report.model_dump()


@app.post("/replan")
def replan_on_contract_change(request: ReplanRequest):
    input_dir = Path(request.input_path)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")

    workflow = TrailerDirectorWorkflow(base_dir=input_dir)
    state = workflow.run()

    changed_rule = ConstraintRule(
        rule_id=request.rule_id,
        type="music_restriction" if "music" in request.scope else "actor_restriction",
        scope=request.scope,
        condition="",
        allowed_behavior="None",
        blocked_behavior=f"Rule {request.rule_id} status changed to {request.status}",
        evidence=["API Contract Amendment"],
        status=ConstraintStatus(request.status),
        expiry_date=request.expiry_date
    )

    updated_state = workflow.trigger_contract_modification(state, changed_rule)
    return {
        "status": "replan_completed",
        "impact_reports": [r.model_dump() for r in updated_state.change_impact_reports],
        "updated_plans": {k: v.model_dump() for k, v in updated_state.trailer_plans.items()}
    }


@app.post("/run")
def run_workflow(request: RunRequest):
    input_dir = Path(request.input_path)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")

    provider_mgr = ProviderManager(preferred_provider=config.llm_provider)
    workflow = TrailerDirectorWorkflow(base_dir=input_dir, provider_manager=provider_mgr)

    if request.audience == "family":
        audiences = [AudienceType.FAMILY]
    elif request.audience == "young_adult":
        audiences = [AudienceType.YOUNG_ADULT]
    elif request.audience == "dialect_region":
        audiences = [AudienceType.DIALECT_REGION]
    else:
        audiences = [AudienceType.FAMILY, AudienceType.YOUNG_ADULT, AudienceType.DIALECT_REGION]

    scenario = None if request.scenario == "none" else request.scenario
    state = workflow.run(selected_audiences=audiences, scenario=scenario)

    return {
        "status": "success",
        "episode_id": state.episode_package.episode_id,
        "title": state.episode_package.title,
        "plans": {k: v.model_dump() for k, v in state.trailer_plans.items()},
        "total_cost_usd": state.total_cost_usd,
    }
