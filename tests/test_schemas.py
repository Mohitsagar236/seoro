"""
Tests for Pydantic schemas — ensures validation rules work correctly.
"""

import pytest

from app.schemas.models import (
    ExtractedEvent,
    ClassifiedIntent,
    IntentType,
    PriorityLevel,
    MeetingStatus,
    IntegrationsInsight,
    DataFusionInsight,
)


class TestExtractedEvent:
    def test_valid_event(self):
        event = ExtractedEvent(
            event_type="feature_request",
            speaker_role="customer",
            topic="dark mode",
            content="Customer asked for dark mode in the mobile app",
            raw_text="Can you guys add dark mode?",
        )
        assert event.event_type == "feature_request"
        assert event.speaker_role == "customer"

    def test_minimal_event(self):
        event = ExtractedEvent(event_type="general")
        assert event.topic is None
        assert event.content is None


class TestClassifiedIntent:
    def test_valid_intent(self):
        intent = ClassifiedIntent(
            intent_type=IntentType.FEATURE_REQUEST,
            priority=PriorityLevel.HIGH,
            confidence=0.92,
            reasoning="Customer explicitly requested a new feature.",
        )
        assert intent.intent_type == IntentType.FEATURE_REQUEST
        assert intent.confidence == 0.92

    def test_confidence_boundary(self):
        intent = ClassifiedIntent(
            intent_type=IntentType.BUG_REPORT,
            priority=PriorityLevel.CRITICAL,
            confidence=1.0,
        )
        assert intent.confidence == 1.0

    def test_confidence_too_high_rejected(self):
        with pytest.raises(Exception):
            ClassifiedIntent(
                intent_type=IntentType.BUG_REPORT,
                priority=PriorityLevel.LOW,
                confidence=1.5,
            )

    def test_confidence_negative_rejected(self):
        with pytest.raises(Exception):
            ClassifiedIntent(
                intent_type=IntentType.GENERAL,
                priority=PriorityLevel.LOW,
                confidence=-0.1,
            )

    def test_integrations_intent_type(self):
        intent = ClassifiedIntent(
            intent_type=IntentType.INTEGRATIONS,
            priority=PriorityLevel.HIGH,
            confidence=0.85,
        )
        assert intent.intent_type == IntentType.INTEGRATIONS

    def test_data_fusion_intent_type(self):
        intent = ClassifiedIntent(
            intent_type=IntentType.DATA_FUSION,
            priority=PriorityLevel.MEDIUM,
            confidence=0.78,
        )
        assert intent.intent_type == IntentType.DATA_FUSION


class TestIntegrationsInsight:
    def test_valid_insight(self):
        insight = IntegrationsInsight(
            integration_name="Salesforce",
            integration_type="crm",
            direction="bidirectional",
            systems_involved=["Salesforce", "Internal CRM"],
            use_case="Sync customer records between internal CRM and Salesforce",
            status="planned",
            priority=PriorityLevel.HIGH,
            confidence=0.9,
        )
        assert insight.integration_name == "Salesforce"
        assert insight.direction == "bidirectional"

    def test_confidence_boundary(self):
        with pytest.raises(Exception):
            IntegrationsInsight(
                integration_name="Stripe",
                integration_type="api",
                direction="inbound",
                use_case="Payment processing",
                status="existing",
                confidence=1.5,
            )


class TestDataFusionInsight:
    def test_valid_insight(self):
        insight = DataFusionInsight(
            fusion_goal="Unified customer view across channels",
            sources=["CRM", "Support tickets", "Analytics"],
            output_target="data warehouse",
            technique="ETL",
            complexity="high",
            priority=PriorityLevel.CRITICAL,
            confidence=0.88,
        )
        assert insight.fusion_goal == "Unified customer view across channels"
        assert len(insight.sources) == 3

    def test_minimal_insight(self):
        insight = DataFusionInsight(
            fusion_goal="Merge logs",
            technique="union",
            complexity="low",
            confidence=0.7,
        )
        assert insight.output_target is None
        assert insight.sources == []


class TestMeetingStatus:
    def test_analyzing_status_exists(self):
        assert MeetingStatus.ANALYZING == "analyzing"

    def test_all_statuses(self):
        assert set(MeetingStatus) == {
            MeetingStatus.PENDING,
            MeetingStatus.TRANSCRIBING,
            MeetingStatus.EXTRACTING,
            MeetingStatus.ANALYZING,
            MeetingStatus.COMPLETED,
            MeetingStatus.FAILED,
        }
