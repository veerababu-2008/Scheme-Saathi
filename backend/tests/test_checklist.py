"""SchemeSaathi AI — Document checklist API tests."""

import pytest

from extensions import db as _db
from app.models.scheme import Scheme, SchemeCategory, SchemeDocument
from app.models.activity import ChecklistProgress


def _seed_scheme_with_docs(app, slug="checklist-scheme"):
    """Create a scheme with 3 documents and return (scheme_id, [doc_ids])."""
    with app.app_context():
        s = Scheme(
            name="Checklist Scheme",
            slug=slug,
            description="Scheme with documents.",
            benefits="Some benefits.",
            level="central",
            verification_status="demo",
            is_active=True,
        )
        _db.session.add(s)
        _db.session.flush()

        doc_ids = []
        for i, (name, mandatory) in enumerate([
            ("Aadhaar Card", True),
            ("Income Certificate", True),
            ("Passport Photo", False),
        ]):
            doc = SchemeDocument(
                scheme_id=s.id,
                document_name=name,
                is_mandatory=mandatory,
                description=f"Required: {name}",
            )
            _db.session.add(doc)
            _db.session.flush()
            doc_ids.append(doc.id)

        _db.session.commit()
        return s.id, doc_ids


class TestGetChecklist:
    """Tests for GET /checklist/<scheme_id>."""

    def test_get_checklist(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app)
        resp = auth_client.get(f"/api/v1/checklist/{sid}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["scheme_id"] == sid
        assert data["total_documents"] == 3
        assert data["collected_count"] == 0
        assert data["completion_pct"] == 0
        assert len(data["documents"]) == 3

    def test_all_documents_pending_initially(self, auth_client, app):
        sid, _ = _seed_scheme_with_docs(app, slug="cl-pending")
        resp = auth_client.get(f"/api/v1/checklist/{sid}")
        docs = resp.get_json()["data"]["documents"]
        assert all(d["status"] == "pending" for d in docs)

    def test_checklist_not_found(self, auth_client):
        resp = auth_client.get("/api/v1/checklist/99999")
        assert resp.status_code == 404

    def test_checklist_unauthenticated(self, client):
        resp = client.get("/api/v1/checklist/1")
        assert resp.status_code == 401

    def test_document_has_multilingual_names(self, auth_client, app):
        sid, _ = _seed_scheme_with_docs(app, slug="cl-i18n")
        resp = auth_client.get(f"/api/v1/checklist/{sid}")
        doc = resp.get_json()["data"]["documents"][0]
        assert "document_name" in doc
        assert "document_name_te" in doc
        assert "document_name_hi" in doc


class TestUpdateDocument:
    """Tests for PUT /checklist/<scheme_id>/documents/<document_id>."""

    def test_mark_collected(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-collect")
        resp = auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[0]}",
            json={"status": "collected"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["status"] == "collected"
        assert data["document_name"] == "Aadhaar Card"

    def test_mark_not_applicable(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-na")
        resp = auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[2]}",
            json={"status": "not_applicable"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "not_applicable"

    def test_toggle_back_to_pending(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-toggle")
        # Mark collected
        auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[0]}",
            json={"status": "collected"},
        )
        # Toggle back
        resp = auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[0]}",
            json={"status": "pending"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "pending"

    def test_invalid_status(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-invalid")
        resp = auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[0]}",
            json={"status": "done"},
        )
        assert resp.status_code == 400

    def test_scheme_not_found(self, auth_client):
        resp = auth_client.put(
            "/api/v1/checklist/99999/documents/1",
            json={"status": "collected"},
        )
        assert resp.status_code == 404

    def test_document_not_found(self, auth_client, app):
        sid, _ = _seed_scheme_with_docs(app, slug="cl-docnf")
        resp = auth_client.put(
            f"/api/v1/checklist/{sid}/documents/99999",
            json={"status": "collected"},
        )
        assert resp.status_code == 404

    def test_completion_updates(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-pct")
        # Mark 2 of 3 collected
        for did in doc_ids[:2]:
            auth_client.put(
                f"/api/v1/checklist/{sid}/documents/{did}",
                json={"status": "collected"},
            )

        resp = auth_client.get(f"/api/v1/checklist/{sid}")
        data = resp.get_json()["data"]
        assert data["collected_count"] == 2
        assert data["completion_pct"] == 66  # 2/3 = 66%


class TestChecklistSummary:
    """Tests for GET /checklist/summary."""

    def test_summary_empty(self, auth_client):
        resp = auth_client.get("/api/v1/checklist/summary")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total_schemes"] == 0
        assert data["schemes"] == []

    def test_summary_with_progress(self, auth_client, app):
        sid, doc_ids = _seed_scheme_with_docs(app, slug="cl-summary")
        auth_client.put(
            f"/api/v1/checklist/{sid}/documents/{doc_ids[0]}",
            json={"status": "collected"},
        )

        resp = auth_client.get("/api/v1/checklist/summary")
        data = resp.get_json()["data"]
        assert data["total_schemes"] == 1
        assert data["schemes"][0]["scheme_id"] == sid
        assert data["schemes"][0]["collected_count"] == 1
