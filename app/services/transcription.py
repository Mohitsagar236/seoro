"""
Transcription service — converts audio files to text using the Deepgram API.

Supports both pre-recorded file uploads and URLs. Returns the full transcript
text along with word-level timestamps from Deepgram's Nova-2 model.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import asyncio

from deepgram import DeepgramClient, DeepgramClientOptions, PrerecordedOptions, FileSource

from app.config import get_settings
from app.logger import get_logger

log = get_logger(__name__)


@dataclass
class TranscriptionResult:
    transcript: str
    duration_seconds: float
    words: list[dict]  # word-level timestamps from Deepgram
    confidence: float


class TranscriptionService:
    """Deepgram-backed speech-to-text service."""

    def __init__(self) -> None:
        settings = get_settings()
        config = DeepgramClientOptions(
            api_key=settings.deepgram_api_key,
            options={"keepalive": "true"},
        )
        self._client = DeepgramClient(config=config)
        self._options = PrerecordedOptions(
            model="nova-2",
            language="en",
            smart_format=True,
            punctuate=True,
            diarize=True,          # speaker detection
            paragraphs=True,
            utterances=True,
            topics=True,
        )

    async def transcribe_file(self, file_path: Path) -> TranscriptionResult:
        """Transcribe a local audio file."""
        log.info("transcription_started", file=str(file_path))

        with open(file_path, "rb") as audio:
            source: FileSource = {"buffer": audio.read()}

        def _sync_transcribe():
            return self._client.listen.rest.v("1").transcribe_file(
                source, self._options, timeout=300.0
            )

        response = await asyncio.to_thread(_sync_transcribe)
        return self._parse_response(response)

    async def transcribe_url(self, audio_url: str) -> TranscriptionResult:
        """Transcribe audio from a publicly accessible URL."""
        log.info("transcription_started", url=audio_url)

        source = {"url": audio_url}

        def _sync_transcribe():
            return self._client.listen.rest.v("1").transcribe_url(
                source, self._options, timeout=300.0
            )

        response = await asyncio.to_thread(_sync_transcribe)
        return self._parse_response(response)

    def _parse_response(self, response) -> TranscriptionResult:
        """Extract transcript, duration, words, and confidence from Deepgram response."""
        results = response.results
        channel = results.channels[0]
        alternative = channel.alternatives[0]

        transcript = alternative.transcript
        confidence = alternative.confidence
        words = [
            {
                "word": w.word,
                "start": w.start,
                "end": w.end,
                "confidence": w.confidence,
                "speaker": getattr(w, "speaker", None),
            }
            for w in alternative.words
        ]

        duration = getattr(results, "duration", 0.0) or (
            words[-1]["end"] if words else 0.0
        )

        log.info(
            "transcription_completed",
            duration=duration,
            word_count=len(words),
            confidence=round(confidence, 3),
        )

        return TranscriptionResult(
            transcript=transcript,
            duration_seconds=duration,
            words=words,
            confidence=confidence,
        )
