"""
Data fusion analysis service — takes events classified as 'data_fusion' and
produces rich, structured data-fusion records using an LLM.

For each distinct data-fusion initiative mentioned in the meeting the LLM returns:
  - fusion_goal, sources, output_target, technique, complexity,
    priority, confidence, raw_text
"""

from __future__ import annotations

import asyncio
import json

from openai import OpenAI

from app.config import get_settings
from app.schemas.models import ExtractedEvent, DataFusionInsight
from app.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an expert data engineer specialising in data integration and fusion.

You will receive a list of meeting events that relate to combining or unifying
data from multiple sources (ETL, data pipelines, multi-source analytics, etc.).
Analyse them and return ONE structured record for EACH distinct data-fusion
initiative discussed.

For each initiative return a JSON object with:
- fusion_goal: one sentence describing what the merged data achieves
- sources: array of data source names or systems being combined
- output_target: where the fused data lands (e.g. "data warehouse", "dashboard", null)
- technique: one of "join", "union", "aggregate", "ETL", "CDC",
  "streaming", "batch", "ML", "unknown"
- complexity: one of "low", "medium", "high"
  (base on number of sources, transformation complexity, and real-time requirements)
- priority: one of "critical", "high", "medium", "low"
- confidence: float 0.0–1.0 indicating how certain you are of this extraction
- raw_text: the exact quote(s) from the event content that support this record

Return ONLY a JSON array. No markdown, no explanation outside the JSON.
If no distinct data-fusion initiatives can be identified, return an empty array [].
"""


class DataFusionService:
    """Extracts structured data-fusion records from data_fusion-typed events."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def analyse(self, events: list[ExtractedEvent]) -> list[DataFusionInsight]:
        """Return a list of structured data-fusion insights from the given events."""
        if not events:
            return []

        log.info("data_fusion_analysis_started", event_count=len(events))

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
                            "Extract structured data-fusion details from these events:\n\n"
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
            for key in ("data_fusion", "fusions", "data", "results", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        insights = [DataFusionInsight.model_validate(i) for i in parsed]
        log.info("data_fusion_analysis_completed", insight_count=len(insights))
        return insights
