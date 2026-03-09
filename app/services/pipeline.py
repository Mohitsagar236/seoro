"""
Pipeline orchestrator — coordinates the full meeting-processing workflow:

    Audio → Transcript → Events → Intents → Integrations & Data Fusion → Storage

Each step updates the meeting status in Supabase so callers can poll progress.
Errors at any stage mark the meeting as 'failed' with a log trail.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

from app.config import get_settings
from app.db import repository as repo
from app.services.transcription import TranscriptionService
from app.services.event_extraction import EventExtractionService
from app.services.intent_classification import IntentClassificationService
from app.services.integrations import IntegrationsService
from app.services.data_fusion import DataFusionService
from app.logger import get_logger

log = get_logger(__name__)


class PipelineOrchestrator:
    """End-to-end meeting processing pipeline."""

    def __init__(self) -> None:
        self.transcription = TranscriptionService()
        self.event_extraction = EventExtractionService()
        self.intent_classification = IntentClassificationService()
        self.integrations = IntegrationsService()
        self.data_fusion = DataFusionService()

    async def process_meeting(
        self,
        meeting_id: str | UUID,
        *,
        file_path: Path | None = None,
        audio_url: str | None = None,
    ) -> dict:
        """
        Run the full pipeline for a single meeting.

        Provide either `file_path` (local upload) or `audio_url` (remote).
        """
        meeting_id = str(meeting_id)

        if not file_path and not audio_url:
            raise ValueError("Provide either file_path or audio_url")

        try:
            # ── Step 1: Transcribe ───────────────────────────
            repo.update_meeting(meeting_id, {"status": "transcribing"})
            log.info("pipeline_step", step="transcription", meeting_id=meeting_id)

            if file_path:
                result = await self.transcription.transcribe_file(file_path)
            else:
                result = await self.transcription.transcribe_url(audio_url)

            # Save transcript to file (requirement: output meeting_transcript.txt)
            settings = get_settings()
            settings.transcript_dir.mkdir(parents=True, exist_ok=True)
            transcript_path = settings.transcript_dir / f"{meeting_id}_transcript.txt"
            transcript_path.write_text(result.transcript, encoding="utf-8")
            log.info("transcript_saved", path=str(transcript_path))

            repo.update_meeting(meeting_id, {
                "transcript": result.transcript,
                "duration_seconds": result.duration_seconds,
                "status": "extracting",
            })

            # ── Step 2: Extract events ───────────────────────
            log.info("pipeline_step", step="event_extraction", meeting_id=meeting_id)
            extracted_events = await self.event_extraction.extract(result.transcript)

            event_rows = repo.create_events_bulk([
                {
                    "meeting_id": meeting_id,
                    "event_type": e.event_type,
                    "speaker_role": e.speaker_role,
                    "topic": e.topic,
                    "content": e.content,
                    "timestamp_start": e.timestamp_start,
                    "timestamp_end": e.timestamp_end,
                    "raw_text": e.raw_text,
                }
                for e in extracted_events
            ])

            # ── Step 3: Classify intents ─────────────────────
            log.info("pipeline_step", step="intent_classification", meeting_id=meeting_id)
            classified_intents = await self.intent_classification.classify(extracted_events)

            intent_rows = []
            for idx, intent in enumerate(classified_intents):
                # Match intent to its source event row (order-preserved)
                event_id = event_rows[idx]["id"] if idx < len(event_rows) else event_rows[-1]["id"]
                intent_rows.append({
                    "event_id": event_id,
                    "meeting_id": meeting_id,
                    "intent_type": intent.intent_type.value,
                    "priority": intent.priority.value,
                    "confidence": intent.confidence,
                    "reasoning": intent.reasoning,
                })

            repo.create_intents_bulk(intent_rows)

            # ── Step 4: Integrations & Data Fusion deep-analysis ─
            log.info("pipeline_step", step="analyzing", meeting_id=meeting_id)
            # Some existing databases may still enforce an older status check
            # that does not include "analyzing". Fall back to "extracting".
            try:
                repo.update_meeting(meeting_id, {"status": "analyzing"})
            except Exception:
                log.warning(
                    "status_fallback",
                    meeting_id=meeting_id,
                    requested_status="analyzing",
                    fallback_status="extracting",
                )
                repo.update_meeting(meeting_id, {"status": "extracting"})

            # Collect events by type; also promote events whose *intent* was
            # classified as integrations/data_fusion even if the raw event_type differs.
            integration_events: list = []
            data_fusion_events: list = []
            for idx, ev in enumerate(extracted_events):
                intent_val = (
                    classified_intents[idx].intent_type.value
                    if idx < len(classified_intents)
                    else None
                )
                if ev.event_type == "integrations" or intent_val == "integrations":
                    integration_events.append(ev)
                elif ev.event_type == "data_fusion" or intent_val == "data_fusion":
                    data_fusion_events.append(ev)

            # Run both analysis services in parallel
            integration_insights, data_fusion_insights = await asyncio.gather(
                self.integrations.analyse(integration_events),
                self.data_fusion.analyse(data_fusion_events),
            )

            if integration_insights:
                repo.create_integration_insights_bulk([
                    {
                        "meeting_id": meeting_id,
                        "integration_name": ins.integration_name,
                        "integration_type": ins.integration_type,
                        "direction": ins.direction,
                        "systems_involved": ins.systems_involved,
                        "use_case": ins.use_case,
                        "status": ins.status,
                        "priority": ins.priority.value,
                        "confidence": ins.confidence,
                        "raw_text": ins.raw_text,
                    }
                    for ins in integration_insights
                ])

            if data_fusion_insights:
                repo.create_data_fusion_insights_bulk([
                    {
                        "meeting_id": meeting_id,
                        "fusion_goal": ins.fusion_goal,
                        "sources": ins.sources,
                        "output_target": ins.output_target,
                        "technique": ins.technique,
                        "complexity": ins.complexity,
                        "priority": ins.priority.value,
                        "confidence": ins.confidence,
                        "raw_text": ins.raw_text,
                    }
                    for ins in data_fusion_insights
                ])

            # ── Done ─────────────────────────────────────────
            repo.update_meeting(meeting_id, {"status": "completed"})
            log.info("pipeline_completed", meeting_id=meeting_id)

            return {
                "meeting_id": meeting_id,
                "status": "completed",
                "events_count": len(event_rows),
                "intents_count": len(intent_rows),
                "integration_insights_count": len(integration_insights),
                "data_fusion_insights_count": len(data_fusion_insights),
            }

        except Exception:
            repo.update_meeting(meeting_id, {"status": "failed"})
            log.exception("pipeline_failed", meeting_id=meeting_id)
            raise
