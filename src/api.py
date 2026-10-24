"""FastAPI Web Service for Autonomous Trailer Director."""
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
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
from src.media.video_processor import VideoProcessor
from src.media.audio_processor import AudioProcessor
from src.media.trailer_renderer import TrailerRenderer


app = FastAPI(
    title="Autonomous Trailer Director API",
    description="Agentic editorial planning and independent verification platform for OTT dialect streaming.",
    version="1.0.0"
)

config = get_config()
INDEX_HTML_PATH = Path(__file__).resolve().parent / "web" / "index.html"


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


class GenerateRequest(BaseModel):
    media_path: Optional[str] = "sample_data/media/real_video.mp4"
    audience: Optional[str] = "family"
    mode: Optional[str] = "replay"
    scenario: Optional[str] = "none"
    input_path: Optional[str] = "sample_data"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_homepage():
    """Serves the interactive Autonomous Trailer Director Studio homepage."""
    if INDEX_HTML_PATH.exists():
        return HTMLResponse(content=INDEX_HTML_PATH.read_text(encoding="utf-8"))
    return RedirectResponse(url="/docs")


@app.get("/home", response_class=HTMLResponse, include_in_schema=False)
def home_redirect():
    """Redirects to root homepage."""
    return RedirectResponse(url="/")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Autonomous Trailer Director",
        "version": "1.0.0",
        "active_provider": config.llm_provider
    }


@app.get("/api/media-list")
def list_available_media():
    """Returns discovered movie / media files in the workspace with metadata."""
    search_dirs = [Path("sample_data/media"), Path("submission/sample_data/media")]
    results = []
    seen = set()
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for mp4_file in sdir.glob("*.mp4"):
            if mp4_file.name in seen or mp4_file.name.startswith("_") or "trailer" in mp4_file.name.lower():
                continue
            seen.add(mp4_file.name)
            meta = VideoProcessor.extract_metadata(mp4_file)
            has_audio, audio_msg = AudioProcessor.detect_audio_stream(mp4_file)
            results.append({
                "filename": mp4_file.name,
                "path": str(mp4_file).replace("\\", "/"),
                "duration_seconds": round(meta.duration_seconds, 1),
                "resolution": f"{meta.width}x{meta.height}",
                "fps": meta.fps,
                "has_audio": has_audio,
                "audio_msg": audio_msg,
                "is_real": "episode_01" not in mp4_file.name.lower()
            })
    return {"media": results}


@app.post("/api/upload")
async def upload_movie(file: UploadFile = File(...)):
    """Uploads a full movie or episode to the director workspace."""
    uploads_dir = Path("sample_data/media/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest_path = uploads_dir / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    meta = VideoProcessor.extract_metadata(dest_path)
    has_audio, audio_msg = AudioProcessor.detect_audio_stream(dest_path)
    return {
        "status": "success",
        "filename": file.filename,
        "path": str(dest_path).replace("\\", "/"),
        "size_bytes": dest_path.stat().st_size,
        "duration_seconds": round(meta.duration_seconds, 1),
        "resolution": f"{meta.width}x{meta.height}",
        "fps": meta.fps,
        "has_audio": has_audio,
        "audio_msg": audio_msg
    }


@app.post("/api/generate")
def generate_trailer_api(request: GenerateRequest):
    """End-to-end pipeline: analyzes movie, plans trailer, validates 10 layers, and renders video with audio."""
    input_dir = Path(request.input_path or "sample_data")
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail=f"Input directory not found: {request.input_path}")

    # Resolve media path
    raw_path = Path(request.media_path or "sample_data/media/real_video.mp4")
    media_path = raw_path.resolve()
    if not media_path.exists():
        candidates = [
            input_dir / "media" / raw_path.name,
            Path("sample_data/media") / raw_path.name,
            Path("submission/sample_data/media") / raw_path.name,
            Path("sample_data/media/real_video.mp4"),
            Path("submission/sample_data/media/real_video.mp4"),
            input_dir / "media" / "episode_01.mp4"
        ]
        for c in candidates:
            if c.exists():
                media_path = c.resolve()
                break

    execution_mode = (request.mode or "replay").lower()
    media_source = "real_media" if "episode_01.mp4" not in media_path.name.lower() else "replay_fixture"

    provider_mgr = ProviderManager(preferred_provider=config.llm_provider if execution_mode == "live" else "mock")
    decision_logger = DecisionLogger()

    workflow = TrailerDirectorWorkflow(
        base_dir=input_dir,
        provider_manager=provider_mgr,
        decision_logger=decision_logger,
        reference_date="2026-02-15",
        media_path=media_path,
        execution_mode=execution_mode,
        media_source=media_source
    )

    if request.audience == "family":
        audiences = [AudienceType.FAMILY]
    elif request.audience == "young_adult":
        audiences = [AudienceType.YOUNG_ADULT]
    elif request.audience == "dialect_region":
        audiences = [AudienceType.DIALECT_REGION]
    else:
        audiences = [AudienceType.FAMILY, AudienceType.YOUNG_ADULT, AudienceType.DIALECT_REGION]

    scenario = None if (not request.scenario or request.scenario == "none") else request.scenario
    state = workflow.run(selected_audiences=audiences, scenario=scenario)

    # Render video for each trailer
    web_trailers_dir = Path("sample_run/web_trailers")
    web_trailers_dir.mkdir(parents=True, exist_ok=True)

    video_urls = {}
    rendered_details = {}
    for aud_key, plan in state.trailer_plans.items():
        out_vid = web_trailers_dir / f"{aud_key}_trailer.mp4"
        render_res = TrailerRenderer.render_trailer(
            plan=plan,
            media_path=media_path,
            output_video_path=out_vid
        )
        video_urls[aud_key] = f"/api/video/{out_vid.name}"
        rendered_details[aud_key] = render_res

    has_audio, _ = AudioProcessor.detect_audio_stream(media_path)

    return {
        "status": "success",
        "episode_id": state.episode_package.episode_id,
        "title": state.episode_package.title,
        "media_source": media_source,
        "media_path": str(media_path),
        "has_audio": has_audio,
        "videos": video_urls,
        "plans": {k: v.model_dump() for k, v in state.trailer_plans.items()},
        "rendered_details": rendered_details,
        "total_cost_usd": state.total_cost_usd,
    }


@app.get("/api/video/{filename}")
def stream_video(filename: str):
    """Streams the rendered trailer MP4 video directly to the browser."""
    search_dirs = [
        Path("sample_run/web_trailers"),
        Path("trailer_run_2"),
        Path("trailer_run"),
        Path("sample_run"),
        Path("submission/sample_run")
    ]
    for d in search_dirs:
        candidate = d / filename
        if candidate.exists():
            return FileResponse(
                path=candidate,
                media_type="video/mp4",
                filename=filename
            )
    raise HTTPException(status_code=404, detail=f"Video file '{filename}' not found.")


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
