"""
Supabase client — single shared instance across the application.

Uses the `supabase` Python SDK. Tables are created via the SQL migration
in `app/db/migrations/001_init.sql` which should be run from the Supabase
dashboard SQL editor or via `psql`.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import create_client, Client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Use service_role key for server-side access (bypasses RLS)."""
    settings = get_settings()
    key = settings.supabase_service_role_key or settings.supabase_key
    return create_client(settings.supabase_url, key)
