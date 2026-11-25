"""SchemeSaathi AI — Auth endpoint tests."""


# ═══════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "GoodPass1234",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["data"]["email"] == "new@example.com"
        assert body["error"] is None

    def test_register_creates_profile(self, client):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "profile@example.com",
                "password": "GoodPass1234",
                "full_name": "Profile User",
            },
        )
        resp = client.get("/api/v1/profile/")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["full_name"] == "Profile User"

    def test_register_sets_cookies(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "cookie@example.com", "password": "GoodPass1234"},
        )
        cookie_header = resp.headers.getlist("Set-Cookie")
        cookie_str = " ".join(cookie_header)
        assert "access_token_cookie" in cookie_str

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@example.com", "password": "GoodPass1234"}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "CONFLICT"

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "GoodPass1234"},
        )
        assert resp.status_code == 400

    def test_register_password_too_short(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "Ab1"},
        )
        assert resp.status_code == 400

    def test_register_password_all_digits(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "digits@example.com", "password": "12345678"},
        )
        assert resp.status_code == 400

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# Login
# ═══════════════════════════════════════════════════════════════════


class TestLogin:
    def test_login_success(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["email"] == registered_user["email"]
        assert body["data"]["role"] == "citizen"
        assert "profile_complete_pct" in body["data"]

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPassword999",
            },
        )
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "ghost@example.com",
                "password": "DoesNotMatter1",
            },
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# Logout
# ═══════════════════════════════════════════════════════════════════


class TestLogout:
    def test_logout_success(self, auth_client):
        resp = auth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200

    def test_logout_invalidates_token(self, auth_client):
        auth_client.post("/api/v1/auth/logout")
        resp = auth_client.get("/api/v1/profile/")
        # After logout the token is blocklisted → 401 or 422
        assert resp.status_code in (401, 422)

    def test_logout_unauthenticated(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# Token Refresh
# ═══════════════════════════════════════════════════════════════════


class TestRefresh:
    def test_refresh_success(self, auth_client):
        resp = auth_client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Password Change
# ═══════════════════════════════════════════════════════════════════


class TestPasswordChange:
    def test_change_password_success(self, auth_client, registered_user):
        resp = auth_client.put(
            "/api/v1/auth/password",
            json={
                "current_password": registered_user["password"],
                "new_password": "BrandNewPass5678",
            },
        )
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, auth_client):
        resp = auth_client.put(
            "/api/v1/auth/password",
            json={
                "current_password": "TotallyWrong999",
                "new_password": "BrandNewPass5678",
            },
        )
        assert resp.status_code == 401

    def test_change_password_weak_new(self, auth_client, registered_user):
        resp = auth_client.put(
            "/api/v1/auth/password",
            json={
                "current_password": registered_user["password"],
                "new_password": "12345678",
            },
        )
        assert resp.status_code == 400

    def test_change_password_unauthenticated(self, client):
        resp = client.put(
            "/api/v1/auth/password",
            json={
                "current_password": "Whatever123",
                "new_password": "NewPass5678",
            },
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# Profile (via auth routes — basic CRUD tested here)
# ═══════════════════════════════════════════════════════════════════


class TestProfileCRUD:
    def test_get_profile(self, auth_client):
        resp = auth_client.get("/api/v1/profile/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["full_name"] == "Test Citizen"
        assert "profile_complete_pct" in body["data"]

    def test_update_profile(self, auth_client):
        resp = auth_client.put(
            "/api/v1/profile/",
            json={
                "state": "Telangana",
                "occupation": "farmer",
                "annual_income": 150000,
                "gender": "male",
                "category": "OBC",
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["state"] == "Telangana"
        assert body["data"]["annual_income"] == 150000
        assert body["data"]["profile_complete_pct"] > 0

    def test_update_profile_invalid_gender(self, auth_client):
        resp = auth_client.put(
            "/api/v1/profile/",
            json={"gender": "invalid_value"},
        )
        assert resp.status_code == 400

    def test_profile_completion(self, auth_client):
        resp = auth_client.get("/api/v1/profile/completion")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "missing_fields" in body["data"]
        assert "total_fields" in body["data"]

    def test_profile_unauthenticated(self, client):
        resp = client.get("/api/v1/profile/")
        assert resp.status_code == 401

    def test_export_data(self, auth_client):
        resp = auth_client.post("/api/v1/profile/export")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "user" in body["data"]
        assert "profile" in body["data"]

    def test_delete_account(self, auth_client):
        resp = auth_client.delete("/api/v1/profile/account")
        assert resp.status_code == 200
        # After deletion, profile should fail
        resp2 = auth_client.get("/api/v1/profile/")
        assert resp2.status_code in (401, 404)
