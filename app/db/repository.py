"""
Repository layer — all Supabase CRUD operations for meetings, events, intents,
integration insights, and data-fusion insights.

Keeps database access isolated from business logic so services never touch
the Supabase client directly.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.client import get_supabase_client
from app.logger import get_logger

log = get_logger(__name__)


# ── Meetings ─────────────────────────────────────────────────

def create_meeting(data: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase_client()
    result = client.table("meetings").insert(data).execute()
    log.info("meeting_created", meeting_id=result.data[0]["id"])
    return result.data[0]


def get_meeting(meeting_id: str | UUID) -> dict[str, Any] | None:
    client = get_supabase_client()
    result = (
        client.table("meetings")
        .select("*")
        .eq("id", str(meeting_id))
        .execute()
    )
    return result.data[0] if result.data else None


def update_meeting(meeting_id: str | UUID, data: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase_client()
    result = (
        client.table("meetings")
        .update(data)
        .eq("id", str(meeting_id))
        .execute()
    )
    return result.data[0]


def list_meetings(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    client = get_supabase_client()
    result = (
        client.table("meetings")
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


# ── Events ───────────────────────────────────────────────────

def create_events_bulk(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    client = get_supabase_client()
    result = client.table("events").insert(events).execute()
    log.info("events_created", count=len(result.data))
    return result.data


def get_events_by_meeting(meeting_id: str | UUID) -> list[dict[str, Any]]:
    client = get_supabase_client()
    result = (
        client.table("events")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at")
        .execute()
    )
    return result.data


# ── Intents ──────────────────────────────────────────────────

def create_intents_bulk(intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not intents:
        return []
    client = get_supabase_client()
    result = client.table("intents").insert(intents).execute()
    log.info("intents_created", count=len(result.data))
    return result.data


def get_intents_by_meeting(meeting_id: str | UUID) -> list[dict[str, Any]]:
    client = get_supabase_client()
    result = (
        client.table("intents")
        .select("*, events(*)")
        .eq("meeting_id", str(meeting_id))
        .order("created_at")
        .execute()
    )
    return result.data


# ── Integration insights ──────────────────────────────────────

def create_integration_insights_bulk(insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not insights:
        return []
    client = get_supabase_client()
    result = client.table("integration_insights").insert(insights).execute()
    log.info("integration_insights_created", count=len(result.data))
    return result.data


def get_integration_insights_by_meeting(meeting_id: str | UUID) -> list[dict[str, Any]]:
    client = get_supabase_client()
    result = (
        client.table("integration_insights")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at")
        .execute()
    )
    return result.data


# ── Data fusion insights ──────────────────────────────────────

def create_data_fusion_insights_bulk(insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not insights:
        return []
    client = get_supabase_client()
    result = client.table("data_fusion_insights").insert(insights).execute()
    log.info("data_fusion_insights_created", count=len(result.data))
    return result.data


def get_data_fusion_insights_by_meeting(meeting_id: str | UUID) -> list[dict[str, Any]]:
    client = get_supabase_client()
    result = (
        client.table("data_fusion_insights")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at")
        .execute()
    )
    return result.data
