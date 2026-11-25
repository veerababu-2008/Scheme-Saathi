"""SchemeSaathi AI — Scheme endpoint tests."""


# ═══════════════════════════════════════════════════════════════════
# List schemes
# ═══════════════════════════════════════════════════════════════════


class TestListSchemes:
    def test_list_returns_schemes(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 5
        assert body["meta"]["total"] == 5
        assert body["error"] is None

    def test_list_pagination(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/?page=1&per_page=2")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 2
        assert body["meta"]["per_page"] == 2
        assert body["meta"]["pages"] == 3  # 5 items / 2 per page

    def test_list_filter_by_level(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/?level=state")
        assert resp.status_code == 200
        body = resp.get_json()
        assert all(s["level"] == "state" for s in body["data"])

    def test_list_filter_by_category(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/?category=education")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) >= 1
        assert "education" in body["data"][0]["categories"]

    def test_list_filter_by_state(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/?state=Telangana")
        assert resp.status_code == 200
        body = resp.get_json()
        # Should include Telangana state schemes AND central schemes
        assert len(body["data"]) >= 3

    def test_list_empty_result(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/?level=central&category=agriculture")
        body = resp.get_json()
        # We have no central agriculture scheme in test data
        assert resp.status_code == 200

    def test_list_invalid_level(self, client):
        resp = client.get("/api/v1/schemes/?level=invalid")
        assert resp.status_code == 400

    def test_list_no_auth_required(self, client, seeded_schemes):
        """Scheme listing is public — no JWT needed."""
        resp = client.get("/api/v1/schemes/")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Search schemes
# ═══════════════════════════════════════════════════════════════════


class TestSearchSchemes:
    def test_search_found(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/search?q=Education")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) >= 1
        assert "education" in body["data"][0]["name"].lower()

    def test_search_case_insensitive(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/search?q=health")
        body = resp.get_json()
        assert len(body["data"]) >= 1

    def test_search_no_results(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/search?q=xyznonexistent999")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 0
        assert body["meta"]["total"] == 0

    def test_search_query_too_short(self, client):
        resp = client.get("/api/v1/schemes/search?q=x")
        assert resp.status_code == 400

    def test_search_missing_query(self, client):
        resp = client.get("/api/v1/schemes/search")
        assert resp.status_code == 400

    def test_search_by_description(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/search?q=Description")
        body = resp.get_json()
        assert len(body["data"]) >= 1


# ═══════════════════════════════════════════════════════════════════
# Scheme detail (by slug)
# ═══════════════════════════════════════════════════════════════════


class TestSchemeDetail:
    def test_get_by_slug(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/test-education")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["slug"] == "test-education"
        assert body["data"]["name"] == "Test Education Scheme"
        assert body["data"]["verification_status"] == "demo"

    def test_detail_includes_documents(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/test-education")
        body = resp.get_json()
        assert len(body["data"]["documents"]) >= 1
        assert body["data"]["documents"][0]["document_name"] == "Aadhaar Card"

    def test_detail_includes_rules(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/test-education")
        body = resp.get_json()
        assert "eligibility_rules" in body["data"]
        assert body["data"]["eligibility_rules"]["rules_json"]["op"] == "AND"

    def test_detail_includes_categories(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/test-education")
        body = resp.get_json()
        assert "education" in body["data"]["categories"]

    def test_nonexistent_slug(self, client):
        resp = client.get("/api/v1/schemes/does-not-exist-at-all")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════════════════════════


class TestCategories:
    def test_list_categories(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/categories")
        assert resp.status_code == 200
        body = resp.get_json()
        cats = body["data"]
        assert isinstance(cats, list)
        assert len(cats) >= 1
        # Each entry has name and count
        assert "name" in cats[0]
        assert "count" in cats[0]

    def test_category_counts_correct(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/categories")
        body = resp.get_json()
        cat_map = {c["name"]: c["count"] for c in body["data"]}
        # We seeded one education scheme
        assert cat_map.get("education") == 1


# ═══════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════


class TestStats:
    def test_scheme_stats(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/stats")
        assert resp.status_code == 200
        body = resp.get_json()
        data = body["data"]
        assert data["total_schemes"] == 5
        assert data["central_schemes"] == 3
        assert data["state_schemes"] == 2
        assert data["categories_covered"] >= 1

    def test_stats_empty_db(self, client):
        resp = client.get("/api/v1/schemes/stats")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total_schemes"] == 0


# ═══════════════════════════════════════════════════════════════════
# Featured
# ═══════════════════════════════════════════════════════════════════


class TestFeatured:
    def test_featured_returns_schemes(self, client, seeded_schemes):
        resp = client.get("/api/v1/schemes/featured")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) <= 6
        assert len(body["data"]) >= 1

    def test_featured_empty_db(self, client):
        resp = client.get("/api/v1/schemes/featured")
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) == 0
