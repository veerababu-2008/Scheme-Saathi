"""SchemeSaathi AI — Feedback API tests."""

import pytest

from extensions import db as _db
from app.models.scheme import Scheme
from app.models.admin import Feedback


def _seed_scheme(app, slug="feedback-scheme"):
    """Create a scheme and return its id."""
    with app.app_context():
        s = Scheme(
            name="Feedback Scheme",
            slug=slug,
            description="A scheme for feedback.",
            benefits="Some benefits.",
            level="central",
            verification_status="demo",
            is_active=True,
        )
        _db.session.add(s)
        _db.session.commit()
        return s.id


class TestSubmitFeedback:
    """Tests for POST /feedback."""

    def test_submit_bug(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={
                "type": "bug",
                "message": "The eligibility check shows wrong status for my age.",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["type"] == "bug"
        assert data["status"] == "open"
        assert data["scheme_id"] is None

    def test_submit_suggestion(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={
                "type": "suggestion",
                "message": "Please add more Telangana state schemes to the platform.",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["type"] == "suggestion"

    def test_submit_correction_with_scheme(self, auth_client, app):
        sid = _seed_scheme(app)
        resp = auth_client.post(
            "/api/v1/feedback",
            json={
                "type": "correction",
                "message": "The benefit amount for this scheme has been updated to ₹8,000.",
                "scheme_id": sid,
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["type"] == "correction"
        assert data["scheme_id"] == sid

    def test_submit_invalid_type(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"type": "complaint", "message": "This is a complaint."},
        )
        assert resp.status_code == 400

    def test_submit_message_too_short(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"type": "bug", "message": "short"},
        )
        assert resp.status_code == 400

    def test_submit_missing_message(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"type": "bug"},
        )
        assert resp.status_code == 400

    def test_submit_missing_type(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"message": "Some long enough message for validation."},
        )
        assert resp.status_code == 400

    def test_submit_nonexistent_scheme(self, auth_client):
        resp = auth_client.post(
            "/api/v1/feedback",
            json={
                "type": "correction",
                "message": "This scheme has wrong information displayed.",
                "scheme_id": 99999,
            },
        )
        assert resp.status_code == 404

    def test_submit_unauthenticated(self, client):
        resp = client.post(
            "/api/v1/feedback",
            json={"type": "bug", "message": "Some bug report with enough length."},
        )
        assert resp.status_code == 401


class TestListFeedback:
    """Tests for GET /feedback."""

    def test_list_empty(self, auth_client):
        resp = auth_client.get("/api/v1/feedback")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_list_own_feedback(self, auth_client):
        auth_client.post(
            "/api/v1/feedback",
            json={"type": "bug", "message": "First bug report with enough text here."},
        )
        auth_client.post(
            "/api/v1/feedback",
            json={"type": "suggestion", "message": "A helpful suggestion for the platform."},
        )

        resp = auth_client.get("/api/v1/feedback")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 2

    def test_filter_by_type(self, auth_client):
        auth_client.post(
            "/api/v1/feedback",
            json={"type": "bug", "message": "A detailed bug report about the issue."},
        )
        auth_client.post(
            "/api/v1/feedback",
            json={"type": "suggestion", "message": "A helpful suggestion for improvement."},
        )

        resp = auth_client.get("/api/v1/feedback?type=bug")
        data = resp.get_json()["data"]
        assert len(data) == 1
        assert data[0]["type"] == "bug"

    def test_list_pagination(self, auth_client):
        for i in range(5):
            auth_client.post(
                "/api/v1/feedback",
                json={"type": "bug", "message": f"Bug report number {i} with enough detail."},
            )

        resp = auth_client.get("/api/v1/feedback?page=1&per_page=2")
        body = resp.get_json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5


class TestGetFeedback:
    """Tests for GET /feedback/<id>."""

    def test_get_own_feedback(self, auth_client):
        create_resp = auth_client.post(
            "/api/v1/feedback",
            json={"type": "bug", "message": "A specific bug that I found in the system."},
        )
        fb_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.get(f"/api/v1/feedback/{fb_id}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == fb_id
        assert resp.get_json()["data"]["type"] == "bug"

    def test_get_not_found(self, auth_client):
        resp = auth_client.get("/api/v1/feedback/99999")
        assert resp.status_code == 404
