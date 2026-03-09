"""
Tests for the API endpoints — uses FastAPI TestClient with mocked services.
"""

import pytest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "seoro"


class TestMeetingsEndpoints:
    @patch("app.routes.meetings.repo")
    def test_list_meetings(self, mock_repo, client):
        mock_repo.list_meetings.return_value = [
            {
                "id": str(uuid4()),
                "title": "Test Meeting",
                "status": "completed",
                "duration_seconds": 120.0,
                "created_at": "2026-03-09T10:00:00Z",
                "updated_at": "2026-03-09T10:05:00Z",
            }
        ]
        response = client.get("/api/v1/meetings")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @patch("app.routes.meetings.repo")
    def test_get_meeting_not_found(self, mock_repo, client):
        mock_repo.get_meeting.return_value = None
        response = client.get(f"/api/v1/meetings/{uuid4()}")
        assert response.status_code == 404

    @patch("app.routes.meetings.repo")
    def test_get_meeting_intent_not_found(self, mock_repo, client):
        mock_repo.get_meeting.return_value = None
        response = client.get(f"/api/v1/meeting-intent/{uuid4()}")
        assert response.status_code == 404

    @patch("app.routes.meetings.repo")
    def test_get_meeting_intent_success(self, mock_repo, client):
        meeting_id = str(uuid4())
        mock_repo.get_meeting.return_value = {
            "id": meeting_id,
            "title": "Test",
            "status": "completed",
            "duration_seconds": 60.0,
            "created_at": "2026-03-09T10:00:00Z",
            "updated_at": "2026-03-09T10:05:00Z",
        }
        mock_repo.get_events_by_meeting.return_value = []
        mock_repo.get_intents_by_meeting.return_value = []

        response = client.get(f"/api/v1/meeting-intent/{meeting_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_id"] == meeting_id
        assert data["detected_intents"] == []
        assert data["extracted_events"] == []

    def test_upload_bad_extension(self, client):
        from io import BytesIO
        response = client.post(
            "/api/v1/meetings/upload",
            files={"file": ("test.txt", BytesIO(b"not audio"), "text/plain")},
        )
        assert response.status_code == 400

    @patch("app.routes.meetings.repo")
    def test_get_integrations_not_found(self, mock_repo, client):
        mock_repo.get_meeting.return_value = None
        response = client.get(f"/api/v1/meetings/{uuid4()}/integrations")
        assert response.status_code == 404

    @patch("app.routes.meetings.repo")
    def test_get_integrations_success(self, mock_repo, client):
        meeting_id = str(uuid4())
        mock_repo.get_meeting.return_value = {
            "id": meeting_id, "title": "Test", "status": "completed",
        }
        mock_repo.get_integration_insights_by_meeting.return_value = []
        response = client.get(f"/api/v1/meetings/{meeting_id}/integrations")
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.routes.meetings.repo")
    def test_get_data_fusion_not_found(self, mock_repo, client):
        mock_repo.get_meeting.return_value = None
        response = client.get(f"/api/v1/meetings/{uuid4()}/data-fusion")
        assert response.status_code == 404

    @patch("app.routes.meetings.repo")
    def test_get_data_fusion_success(self, mock_repo, client):
        meeting_id = str(uuid4())
        mock_repo.get_meeting.return_value = {
            "id": meeting_id, "title": "Test", "status": "completed",
        }
        mock_repo.get_data_fusion_insights_by_meeting.return_value = []
        response = client.get(f"/api/v1/meetings/{meeting_id}/data-fusion")
        assert response.status_code == 200
        assert response.json() == []
