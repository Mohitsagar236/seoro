"""
Integrations analysis service — takes events classified as 'integrations' and
produces rich, structured integration records using an LLM.

For each distinct integration mentioned in the meeting the LLM returns:
  - integration_name, integration_type, direction, systems_involved,
    use_case, status, priority, confidence, raw_text
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI

from app.config import get_settings
from app.schemas.models import ExtractedEvent, IntegrationsInsight
from app.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert solutions architect specialising in system integrations.

You will receive a list of meeting events that relate to integrations/APIs/connectors.
Analyse them and return ONE structured record for EACH distinct integration discussed.

For each integration return a JSON object with:
- integration_name: the specific system, API, or tool (e.g. "Salesforce", "Stripe", "internal CRM")
- integration_type: one of "api", "webhook", "crm", "erp", "data_pipeline",
  "messaging", "analytics", "auth", "storage", "custom"
- direction: one of "inbound", "outbound", "bidirectional", "unknown"
- systems_involved: array of system/service names mentioned with this integration
- use_case: one sentence describing the business purpose
- status: one of "requested", "planned", "in_progress", "existing"
- priority: one of "critical", "high", "medium", "low"
- confidence: float 0.0–1.0 indicating how certain you are of this extraction
- raw_text: the exact quote(s) from the event content that support this record

Return ONLY a JSON array. No markdown, no explanation outside the JSON.
If no distinct integrations can be identified, return an empty array [].
"""


class IntegrationsService:
    """Extracts structured integration records from integration-typed events."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def analyse(self, events: list[ExtractedEvent]) -> list[IntegrationsInsight]:
        """Return a list of structured integration insights from the given events."""
        if not events:
            return []

        log.info("integrations_analysis_started", event_count=len(events))

        events_payload = [e.model_dump(mode="json") for e in events]

        def _sync_call():
            return self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Extract structured integration details from these events:\n\n"
                            f"{json.dumps(events_payload, indent=2)}"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=4096,
            )

        response = await asyncio.to_thread(_sync_call)

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # Unwrap common wrapper keys
        if isinstance(parsed, dict):
            for key in ("integrations", "data", "results", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        insights = [IntegrationsInsight.model_validate(i) for i in parsed]
        log.info("integrations_analysis_completed", insight_count=len(insights))
        return insights
