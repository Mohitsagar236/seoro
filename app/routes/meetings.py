"""
Meeting routes — upload audio, check status, retrieve intent data.

Endpoints
---------
POST   /meetings/upload                       Upload audio file → start pipeline
POST   /meetings/process-url                  Submit audio URL → start pipeline
GET    /meetings                               List all meetings
GET    /meetings/{meeting_id}                  Full meeting detail (transcript + events + intents)
GET    /meetings/{meeting_id}/integrations     Integration insights for a meeting
GET    /meetings/{meeting_id}/data-fusion      Data-fusion insights for a meeting
GET    /meeting-intent/{meeting_id}            Structured intent response (as per spec)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks

from app.config import get_settings
from app.db import repository as repo
from app.logger import get_logger
from app.services.pipeline import PipelineOrchestrator
from app.schemas.models import (
    MeetingResponse,
    MeetingDetailResponse,
    MeetingIntentResponse,
    PipelineStatusResponse,
    MeetingStatus,
    IntegrationInsightResponse,
    DataFusionInsightResponse,
)

router = APIRouter()
log = get_logger(__name__)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".mp4", ".m4a", ".webm", ".ogg", ".flac"}


def _validate_audio_file(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )


async def _run_pipeline(meeting_id: str, *, file_path: Path | None = None, audio_url: str | None = None):
    """Background task wrapper — runs the pipeline and logs failures."""
    try:
        # Build service clients lazily so app startup does not depend on external API keys.
        pipeline = PipelineOrchestrator()
        await pipeline.process_meeting(meeting_id, file_path=file_path, audio_url=audio_url)
    except Exception:
        # Keep endpoint responsive while preserving observability for background failures.
        log.exception("background_pipeline_failed", meeting_id=meeting_id)


# ── Upload audio file ────────────────────────────────────────

@router.post("/meetings/upload", response_model=PipelineStatusResponse, status_code=202)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=None),
):
    """Upload an audio file to start the intent extraction pipeline."""
    _validate_audio_file(file)

    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # Create meeting record first
    meeting = repo.create_meeting({
        "title": title or file.filename,
        "status": "pending",
    })
    meeting_id = meeting["id"]

    # Save file to disk
    safe_filename = f"{meeting_id}{Path(file.filename or '.wav').suffix.lower()}"
    file_path = settings.upload_dir / safe_filename
    with open(file_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # Kick off pipeline in background
    background_tasks.add_task(_run_pipeline, meeting_id, file_path=file_path)

    return PipelineStatusResponse(
        meeting_id=meeting_id,
        status=MeetingStatus.PENDING,
        message="Pipeline started. Poll GET /api/v1/meetings/{meeting_id} for progress.",
    )


# ── Process audio from URL ───────────────────────────────────

@router.post("/meetings/process-url", response_model=PipelineStatusResponse, status_code=202)
async def process_meeting_url(
    background_tasks: BackgroundTasks,
    audio_url: str = Form(...),
    title: str = Form(default=None),
):
    """Submit an audio URL to start the intent extraction pipeline."""
    meeting = repo.create_meeting({
        "title": title or "Meeting from URL",
        "audio_url": audio_url,
        "status": "pending",
    })
    meeting_id = meeting["id"]

    background_tasks.add_task(_run_pipeline, meeting_id, audio_url=audio_url)

    return PipelineStatusResponse(
        meeting_id=meeting_id,
        status=MeetingStatus.PENDING,
        message="Pipeline started. Poll GET /api/v1/meetings/{meeting_id} for progress.",
    )


# ── List meetings ────────────────────────────────────────────

@router.get("/meetings", response_model=list[MeetingResponse])
async def list_meetings(limit: int = 50, offset: int = 0):
    rows = repo.list_meetings(limit=limit, offset=offset)
    return rows


# ── Get meeting detail ───────────────────────────────────────

@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(meeting_id: UUID):
    meeting = repo.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    events = repo.get_events_by_meeting(meeting_id)
    intents = repo.get_intents_by_meeting(meeting_id)

    return {**meeting, "events": events, "intents": intents}


# ── Get meeting intent (spec endpoint) ──────────────────────

@router.get("/meeting-intent/{meeting_id}", response_model=MeetingIntentResponse)
async def get_meeting_intent(meeting_id: UUID):
    """
    Returns structured intent data for a meeting.

    Response includes: meeting_id, detected_intents, extracted_events
    """
    meeting = repo.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    events = repo.get_events_by_meeting(meeting_id)
    intents = repo.get_intents_by_meeting(meeting_id)

    return MeetingIntentResponse(
        meeting_id=meeting["id"],
        title=meeting.get("title"),
        status=meeting["status"],
        detected_intents=intents,
        extracted_events=events,
    )


# ── Get integration insights ─────────────────────────────────

@router.get("/meetings/{meeting_id}/integrations", response_model=list[IntegrationInsightResponse])
async def get_meeting_integrations(meeting_id: UUID):
    """Return all integration insights extracted for a meeting."""
    meeting = repo.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return repo.get_integration_insights_by_meeting(meeting_id)


# ── Get data fusion insights ─────────────────────────────────

@router.get("/meetings/{meeting_id}/data-fusion", response_model=list[DataFusionInsightResponse])
async def get_meeting_data_fusion(meeting_id: UUID):
    """Return all data-fusion insights extracted for a meeting."""
    meeting = repo.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return repo.get_data_fusion_insights_by_meeting(meeting_id)


# ── Root-level spec endpoint (mounted without /api/v1 prefix) ────

intent_router = APIRouter()
intent_router.add_api_route(
    "/meeting-intent/{meeting_id}",
    get_meeting_intent,
    methods=["GET"],
    response_model=MeetingIntentResponse,
    tags=["meeting-intent"],
)
