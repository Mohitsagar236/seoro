"""
Event extraction service — uses OpenAI GPT to detect structured events
from a meeting transcript.

The LLM receives the full transcript and returns a JSON array of
`ExtractedEvent` objects. We enforce structured output via a strict
system prompt and JSON-mode.
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI

from app.config import get_settings
from app.schemas.models import ExtractedEvent
from app.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert transcript analyst. Given ANY transcript (meeting, pitch,
interview, presentation, or conversation), extract ALL meaningful events and
talking points. Always extract at least one event if the transcript has content.

For each event, return a JSON object with these fields:

- event_type: one of "feature_request", "bug_report", "customer_feedback",
  "strategy_discussion", "task_assignment", "integrations", "data_fusion", "general"
  Use "integrations" for any discussion about system integrations, APIs, webhooks,
  third-party connectors, or cross-system data flow.
  Use "data_fusion" for any discussion about combining, merging, or unifying data
  from multiple sources, data pipelines, ETL, or multi-source analytics.
  Use "general" for introductions, pitches, presentations, or anything
  that doesn't fit the other categories.
- speaker_role: one of "customer", "founder", "employee", or null if unknown
- topic: the key feature, product area, or subject mentioned
- content: a 1–2 sentence summary of what was said
- timestamp_start: approximate start time in the transcript (e.g. "00:02:15") or null
- timestamp_end: approximate end time or null
- raw_text: the exact quote(s) from the transcript that support this event

Return ONLY a JSON array of objects. No markdown, no explanation.
Even for a simple pitch or introduction, extract the key topics discussed.
"""


class EventExtractionService:
    """Extracts structured events from meeting transcripts via OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        base_url = settings.openai_base_url
        # OpenRouter keys typically start with sk-or-v1 and need OpenRouter base URL.
        if not base_url and settings.openai_api_key.startswith("sk-or-v1"):
            base_url = "https://openrouter.ai/api/v1"
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=base_url)
        self._model = settings.openai_model

    async def extract(self, transcript: str) -> list[ExtractedEvent]:
        log.info("event_extraction_started", transcript_length=len(transcript))

        def _sync_call():
            return self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Extract all events from this meeting transcript:\n\n"
                            f"{transcript}"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=4096,
            )

        response = await asyncio.to_thread(_sync_call)

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # The model may wrap the array in a key like {"events": [...]}
        if isinstance(parsed, dict):
            for key in ("events", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        events = [ExtractedEvent.model_validate(e) for e in parsed]

        log.info("event_extraction_completed", event_count=len(events))
        return events
