"""SchemeSaathi AI — Admin routes and RBAC test suite."""

import pytest
from extensions import db
from app.models.admin import AdminUser, AuditLog, Feedback
from app.models.activity import EligibilityCheck
from app.models.scheme import Scheme, EligibilityRule


@pytest.fixture()
def admin_users(app):
    """Seed three admin users with super, editor, and viewer roles."""
    with app.app_context():
        super_admin = AdminUser(
            email="super@schemesaathi.in",
            display_name="Super Admin",
            role="super",
            is_active=True,
        )
        super_admin.set_password("SuperSecret123!")

        editor_admin = AdminUser(
            email="editor@schemesaathi.in",
            display_name="Editor Admin",
            role="editor",
            is_active=True,
        )
        editor_admin.set_password("EditorSecret123!")

        viewer_admin = AdminUser(
            email="viewer@schemesaathi.in",
            display_name="Viewer Admin",
            role="viewer",
            is_active=True,
        )
        viewer_admin.set_password("ViewerSecret123!")

        inactive_admin = AdminUser(
            email="inactive@schemesaathi.in",
            display_name="Inactive Admin",
            role="editor",
            is_active=False,
        )
        inactive_admin.set_password("InactivePass123!")

        db.session.add_all([super_admin, editor_admin, viewer_admin, inactive_admin])
        db.session.commit()

        return {
            "super": "super@schemesaathi.in",
            "editor": "editor@schemesaathi.in",
            "viewer": "viewer@schemesaathi.in",
            "inactive": "inactive@schemesaathi.in",
        }


def login_admin(client, email, password):
    return client.post("/api/v1/admin/login", json={"email": email, "password": password})


# ── 1. Admin Authentication Tests ────────────────────────────────


class TestAdminAuth:
    def test_login_success(self, client, admin_users):
        resp = login_admin(client, "super@schemesaathi.in", "SuperSecret123!")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["admin"]["email"] == "super@schemesaathi.in"
        assert body["data"]["admin"]["role"] == "super"

        cookies = resp.headers.getlist("Set-Cookie")
        assert any("access_token_cookie" in c for c in cookies)

    def test_login_invalid_password(self, client, admin_users):
        resp = login_admin(client, "super@schemesaathi.in", "WrongPassword!")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_login_inactive_admin(self, client, admin_users):
        resp = login_admin(client, "inactive@schemesaathi.in", "InactivePass123!")
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_login_validation_error(self, client, admin_users):
        resp = client.post("/api/v1/admin/login", json={"email": "not-an-email"})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_get_me_success(self, client, admin_users):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        resp = client.get("/api/v1/admin/me")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["admin"]["role"] == "editor"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/v1/admin/me")
        assert resp.status_code == 401


# ── 2. RBAC Access Control Tests ─────────────────────────────────


class TestAdminRBAC:
    def test_citizen_token_rejected_on_admin_endpoint(self, auth_client, admin_users):
        resp = auth_client.get("/api/v1/admin/me")
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN"

    def test_viewer_cannot_create_scheme(self, client, admin_users):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.post("/api/v1/admin/schemes", json={
            "name": "Unauthorized Scheme",
            "description": "Viewer trying to create a scheme.",
            "benefits": "Free benefits",
        })
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN"

    def test_editor_cannot_delete_scheme(self, client, admin_users, seeded_schemes):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        resp = client.delete("/api/v1/admin/schemes/1")
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN"

    def test_super_can_delete_scheme(self, client, admin_users, seeded_schemes):
        login_admin(client, "super@schemesaathi.in", "SuperSecret123!")
        resp = client.delete("/api/v1/admin/schemes/1")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted"] is True


# ── 3. Scheme Management CRUD Tests ──────────────────────────────


class TestAdminSchemeCRUD:
    def test_list_schemes_admin(self, client, admin_users, seeded_schemes):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.get("/api/v1/admin/schemes?per_page=10")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) >= 5

    def test_list_schemes_filter_category(self, client, admin_users, seeded_schemes):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.get("/api/v1/admin/schemes?category=health")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all("health" in s["categories"] for s in data)

    def test_create_scheme_with_relations(self, client, admin_users):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        payload = {
            "name": "Pradhan Mantri Admin Scheme",
            "slug": "pm-admin-scheme",
            "description": "Comprehensive scheme created via admin portal.",
            "benefits": "Subsidised grant up to 50000 rupees.",
            "level": "central",
            "verification_status": "verified",
            "categories": ["education", "finance"],
            "documents": [
                {"document_name": "Ration Card", "is_mandatory": True}
            ],
            "sources": [
                {"title": "Gazette Notification", "url": "https://egazette.gov.in/test"}
            ],
        }
        resp = client.post("/api/v1/admin/schemes", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["slug"] == "pm-admin-scheme"
        assert "education" in data["categories"]
        assert len(data["documents"]) == 1

        # Check audit log was created
        audit_resp = client.get("/api/v1/admin/audit-logs?type=scheme")
        assert audit_resp.status_code == 200
        logs = audit_resp.get_json()["data"]
        assert any(l["action"] == "create_scheme" for l in logs)

    def test_create_scheme_duplicate_slug(self, client, admin_users, seeded_schemes):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        payload = {
            "name": "Test Duplicate Scheme",
            "slug": "test-education",
            "description": "Trying to duplicate an existing slug.",
            "benefits": "Benefits here.",
        }
        resp = client.post("/api/v1/admin/schemes", json=payload)
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "CONFLICT"

    def test_get_scheme_detail(self, client, admin_users, seeded_schemes):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.get("/api/v1/admin/schemes/1")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == 1

    def test_update_scheme(self, client, admin_users, seeded_schemes):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        resp = client.put("/api/v1/admin/schemes/1", json={
            "verification_status": "verified",
            "max_benefit_amount": 75000,
        })
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["verification_status"] == "verified"
        assert data["max_benefit_amount"] == 75000

    def test_hard_delete_scheme(self, client, admin_users, seeded_schemes):
        login_admin(client, "super@schemesaathi.in", "SuperSecret123!")
        resp = client.delete("/api/v1/admin/schemes/2?hard=true")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["hard"] is True

        # Verify not found
        get_resp = client.get("/api/v1/admin/schemes/2")
        assert get_resp.status_code == 404


# ── 4. Eligibility Rule Management Tests ─────────────────────────


class TestAdminRules:
    def test_list_rules(self, client, admin_users, seeded_schemes):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.get("/api/v1/admin/schemes/1/rules")
        assert resp.status_code == 200
        rules = resp.get_json()["data"]
        assert len(rules) >= 1
        assert rules[0]["version"] == 1

    def test_create_new_rule_version(self, client, admin_users, seeded_schemes):
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        payload = {
            "rules_json": {
                "op": "AND",
                "rules": [
                    {"field": "age", "cmp": "gte", "value": 21, "mandatory": True}
                ],
            },
            "notes": "Updated minimum age to 21",
        }
        resp = client.post("/api/v1/admin/schemes/1/rules", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["version"] == 2
        assert data["is_active"] is True

        # Verify old rule deactivated
        list_resp = client.get("/api/v1/admin/schemes/1/rules")
        all_rules = list_resp.get_json()["data"]
        v1 = next(r for r in all_rules if r["version"] == 1)
        assert v1["is_active"] is False


# ── 5. Feedback Moderation Tests ─────────────────────────────────


class TestAdminFeedback:
    def test_list_and_update_feedback(self, client, admin_users, auth_client):
        # Submit feedback as citizen
        submit_resp = auth_client.post("/api/v1/feedback", json={
            "type": "bug",
            "message": "Button does not click on mobile device.",
        })
        assert submit_resp.status_code == 201
        fb_id = submit_resp.get_json()["data"]["id"]

        # Login as editor admin
        login_admin(client, "editor@schemesaathi.in", "EditorSecret123!")
        list_resp = client.get("/api/v1/admin/feedback?status=open")
        assert list_resp.status_code == 200
        items = list_resp.get_json()["data"]
        assert any(i["id"] == fb_id for i in items)

        # Update feedback status
        patch_resp = client.patch(f"/api/v1/admin/feedback/{fb_id}", json={"status": "reviewed"})
        assert patch_resp.status_code == 200
        assert patch_resp.get_json()["data"]["status"] == "reviewed"


# ── 6. Analytics & Audit Logs Tests ──────────────────────────────


class TestAdminAnalyticsAndAudit:
    def test_get_analytics(self, client, admin_users, seeded_schemes):
        login_admin(client, "viewer@schemesaathi.in", "ViewerSecret123!")
        resp = client.get("/api/v1/admin/analytics")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "schemes" in data
        assert "citizens" in data
        assert "eligibility" in data
        assert "feedback" in data
        assert data["schemes"]["total"] >= 5

    def test_audit_logs_query(self, client, admin_users):
        login_admin(client, "super@schemesaathi.in", "SuperSecret123!")
        resp = client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 200
        assert "data" in resp.get_json()
        assert "meta" in resp.get_json()
