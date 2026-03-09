"""
Intent classification service — takes extracted events and classifies each
into a higher-level intent with priority and confidence.

Uses OpenAI GPT with structured JSON output.
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI

from app.config import get_settings
from app.schemas.models import ExtractedEvent, ClassifiedIntent
from app.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert at classifying meeting events into business intents.

For EACH event provided, return a JSON object with:
- intent_type: one of "feature_request", "bug_report", "customer_feedback",
  "strategy_discussion", "task_assignment", "integrations", "data_fusion", "general"
  Use "integrations" when the event involves connecting systems, APIs, webhooks,
  third-party services, or cross-system data movement.
  Use "data_fusion" when the event involves combining or unifying data from multiple
  sources, ETL pipelines, data merging, or multi-source analysis.
- priority: one of "critical", "high", "medium", "low"
  (base this on urgency words, customer impact, and business value)
- confidence: a float between 0.0 and 1.0 indicating how certain you are
- reasoning: a brief 1-sentence explanation of why you chose this intent and priority

Return ONLY a JSON array with one classification per input event, in the same order.
No markdown, no explanation outside the JSON.
"""


class IntentClassificationService:
    """Classifies extracted events into business intents."""

    def __init__(self) -> None:
        settings = get_settings()
        base_url = settings.openai_base_url
        # OpenRouter keys typically start with sk-or-v1 and need OpenRouter base URL.
        if not base_url and settings.openai_api_key.startswith("sk-or-v1"):
            base_url = "https://openrouter.ai/api/v1"
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=base_url)
        self._model = settings.openai_model

    async def classify(self, events: list[ExtractedEvent]) -> list[ClassifiedIntent]:
        if not events:
            return []

        log.info("intent_classification_started", event_count=len(events))

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
                            "Classify these meeting events:\n\n"
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

        # Handle wrapper objects
        if isinstance(parsed, dict):
            for key in ("intents", "classifications", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        intents = [ClassifiedIntent.model_validate(i) for i in parsed]

        log.info("intent_classification_completed", intent_count=len(intents))
        return intents
