"""
Pydantic models — shared request / response schemas for the entire app.

These schemas enforce validation at the API boundary and also type the data
flowing between pipeline stages.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────

class MeetingStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class IntentType(str, Enum):
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    CUSTOMER_FEEDBACK = "customer_feedback"
    STRATEGY_DISCUSSION = "strategy_discussion"
    TASK_ASSIGNMENT = "task_assignment"
    INTEGRATIONS = "integrations"
    DATA_FUSION = "data_fusion"
    GENERAL = "general"


class PriorityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Event schemas ────────────────────────────────────────────

class EventBase(BaseModel):
    event_type: str = Field(..., description="Type of event detected in transcript")
    speaker_role: Optional[str] = Field(None, description="customer | founder | employee")
    topic: Optional[str] = Field(None, description="Key feature or topic mentioned")
    content: Optional[str] = Field(None, description="Summary of the event")
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None
    raw_text: Optional[str] = Field(None, description="Original transcript segment")


class EventResponse(EventBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# ── Intent schemas ───────────────────────────────────────────

class IntentBase(BaseModel):
    intent_type: IntentType
    priority: PriorityLevel = PriorityLevel.MEDIUM
    confidence: float = Field(..., ge=0.0, le=1.0, description="0–1 confidence score")
    reasoning: Optional[str] = None


class IntentCreate(IntentBase):
    event_id: UUID
    meeting_id: UUID


class IntentResponse(IntentBase):
    id: UUID
    event_id: UUID
    meeting_id: UUID
    created_at: datetime
    event: Optional[EventResponse] = None


# ── Meeting schemas ──────────────────────────────────────────

class MeetingResponse(BaseModel):
    id: UUID
    title: Optional[str]
    status: MeetingStatus
    duration_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class MeetingDetailResponse(MeetingResponse):
    transcript: Optional[str] = None
    events: list[EventResponse] = Field(default_factory=list)
    intents: list[IntentResponse] = Field(default_factory=list)


# ── Pipeline output (internal) ───────────────────────────────

class ExtractedEvent(BaseModel):
    """Schema that the LLM returns for each detected event."""
    event_type: str
    speaker_role: Optional[str] = None
    topic: Optional[str] = None
    content: Optional[str] = None
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None
    raw_text: Optional[str] = None


class ClassifiedIntent(BaseModel):
    """Schema that the LLM returns for each intent classification."""
    intent_type: IntentType
    priority: PriorityLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None


# ── API response wrappers ────────────────────────────────────

class MeetingIntentResponse(BaseModel):
    """Response for GET /meeting-intent/{meeting_id}"""
    meeting_id: UUID
    title: Optional[str]
    status: MeetingStatus
    detected_intents: list[IntentResponse]
    extracted_events: list[EventResponse]


class PipelineStatusResponse(BaseModel):
    meeting_id: UUID
    status: MeetingStatus
    message: str


# ── Integrations schemas ─────────────────────────────────────

class IntegrationsInsight(BaseModel):
    """Structured details for a single integration identified in the meeting."""
    integration_name: str = Field(..., description="Name of the system/tool being integrated")
    integration_type: str = Field(
        ...,
        description="api | webhook | crm | erp | data_pipeline | messaging | analytics | auth | storage | custom",
    )
    direction: str = Field(
        ...,
        description="inbound | outbound | bidirectional | unknown",
    )
    systems_involved: list[str] = Field(default_factory=list)
    use_case: str = Field(..., description="Business purpose of the integration")
    status: str = Field(
        ...,
        description="requested | planned | in_progress | existing",
    )
    priority: PriorityLevel = PriorityLevel.MEDIUM
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class IntegrationInsightResponse(IntegrationsInsight):
    id: UUID
    meeting_id: UUID
    event_id: Optional[UUID] = None
    created_at: datetime


# ── Data fusion schemas ──────────────────────────────────────

class DataFusionInsight(BaseModel):
    """Structured details for a single data-fusion initiative identified in the meeting."""
    fusion_goal: str = Field(..., description="What the merged / unified data achieves")
    sources: list[str] = Field(default_factory=list, description="Data sources being combined")
    output_target: Optional[str] = Field(None, description="Destination for the fused data")
    technique: str = Field(
        ...,
        description="join | union | aggregate | ETL | CDC | streaming | batch | ML | unknown",
    )
    complexity: str = Field(..., description="low | medium | high")
    priority: PriorityLevel = PriorityLevel.MEDIUM
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class DataFusionInsightResponse(DataFusionInsight):
    id: UUID
    meeting_id: UUID
    event_id: Optional[UUID] = None
    created_at: datetime
