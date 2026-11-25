"""SchemeSaathi AI — Saved schemes (bookmarks) API tests."""

import pytest

from extensions import db as _db
from app.models.scheme import Scheme, SchemeCategory
from app.models.activity import SavedScheme


def _seed_scheme(app, slug="test-save-scheme"):
    """Create a single active scheme and return its id."""
    with app.app_context():
        s = Scheme(
            name="Saveable Scheme",
            slug=slug,
            description="A scheme to bookmark.",
            benefits="Good benefits.",
            level="central",
            verification_status="demo",
            is_active=True,
            max_benefit_amount=10000,
        )
        _db.session.add(s)
        _db.session.flush()
        _db.session.add(SchemeCategory(scheme_id=s.id, category="education"))
        _db.session.commit()
        return s.id


class TestSaveScheme:
    """Tests for POST /saved."""

    def test_save_scheme(self, auth_client, app):
        sid = _seed_scheme(app)
        resp = auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["scheme_id"] == sid
        assert "scheme" in data
        assert data["scheme"]["name"] == "Saveable Scheme"

    def test_save_with_notes(self, auth_client, app):
        sid = _seed_scheme(app, slug="save-notes")
        resp = auth_client.post(
            "/api/v1/saved",
            json={"scheme_id": sid, "notes": "Check eligibility later"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["notes"] == "Check eligibility later"

    def test_save_duplicate(self, auth_client, app):
        sid = _seed_scheme(app, slug="save-dup")
        auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        resp = auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        assert resp.status_code == 409

    def test_save_nonexistent_scheme(self, auth_client):
        resp = auth_client.post("/api/v1/saved", json={"scheme_id": 99999})
        assert resp.status_code == 404

    def test_save_missing_scheme_id(self, auth_client):
        resp = auth_client.post("/api/v1/saved", json={})
        assert resp.status_code == 400

    def test_save_unauthenticated(self, client):
        resp = client.post("/api/v1/saved", json={"scheme_id": 1})
        assert resp.status_code == 401


class TestListSaved:
    """Tests for GET /saved."""

    def test_list_empty(self, auth_client):
        resp = auth_client.get("/api/v1/saved")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_list_with_bookmarks(self, auth_client, app):
        s1 = _seed_scheme(app, slug="list-1")
        s2 = _seed_scheme(app, slug="list-2")
        auth_client.post("/api/v1/saved", json={"scheme_id": s1})
        auth_client.post("/api/v1/saved", json={"scheme_id": s2})

        resp = auth_client.get("/api/v1/saved")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 2

    def test_list_pagination(self, auth_client, app):
        for i in range(5):
            sid = _seed_scheme(app, slug=f"page-{i}")
            auth_client.post("/api/v1/saved", json={"scheme_id": sid})

        resp = auth_client.get("/api/v1/saved?page=1&per_page=2")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5

    def test_list_includes_scheme_details(self, auth_client, app):
        sid = _seed_scheme(app, slug="list-detail")
        auth_client.post("/api/v1/saved", json={"scheme_id": sid})

        resp = auth_client.get("/api/v1/saved")
        entry = resp.get_json()["data"][0]
        assert "scheme" in entry
        assert entry["scheme"]["name"] == "Saveable Scheme"


class TestUpdateNotes:
    """Tests for PATCH /saved/<id>."""

    def test_update_notes(self, auth_client, app):
        sid = _seed_scheme(app, slug="update-notes")
        create_resp = auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        saved_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.patch(
            f"/api/v1/saved/{saved_id}",
            json={"notes": "Updated notes here"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["notes"] == "Updated notes here"

    def test_update_not_found(self, auth_client):
        resp = auth_client.patch(
            "/api/v1/saved/99999",
            json={"notes": "nope"},
        )
        assert resp.status_code == 404

    def test_update_missing_notes(self, auth_client, app):
        sid = _seed_scheme(app, slug="update-missing")
        create_resp = auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        saved_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.patch(f"/api/v1/saved/{saved_id}", json={})
        assert resp.status_code == 400


class TestDeleteSaved:
    """Tests for DELETE /saved/<id>."""

    def test_delete_bookmark(self, auth_client, app):
        sid = _seed_scheme(app, slug="delete-bm")
        create_resp = auth_client.post("/api/v1/saved", json={"scheme_id": sid})
        saved_id = create_resp.get_json()["data"]["id"]

        resp = auth_client.delete(f"/api/v1/saved/{saved_id}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted"] == saved_id

        # Verify gone
        list_resp = auth_client.get("/api/v1/saved")
        assert len(list_resp.get_json()["data"]) == 0

    def test_delete_not_found(self, auth_client):
        resp = auth_client.delete("/api/v1/saved/99999")
        assert resp.status_code == 404
