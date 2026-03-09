"""
Application settings — loaded from environment variables / .env file.

All external credentials and tunables live here. Services import `settings`
directly and never touch os.environ themselves.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ── Supabase ─────────────────────────────
    supabase_url: str
    supabase_key: str  # anon key or service-role key
    supabase_service_role_key: str = ""

    # ── Deepgram ─────────────────────────────
    deepgram_api_key: str

    # ── OpenAI ───────────────────────────────
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # ── Pipeline ─────────────────────────────
    max_audio_duration_seconds: int = 7200
    max_concurrent_pipelines: int = 4

    # ── Storage paths ────────────────────────
    upload_dir: Path = Path("./uploads")
    transcript_dir: Path = Path("./transcripts")


@lru_cache
def get_settings() -> Settings:
    """Singleton accessor — cached after first call."""
    return Settings()  # type: ignore[call-arg]
