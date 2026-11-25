"""SchemeSaathi AI — Recommendation engine tests.

Tests the scorer (component scores, ranking, reasons), weights,
and API endpoints.
"""

from datetime import UTC, datetime, timedelta

from app.models.scheme import EligibilityRule, Scheme, SchemeCategory
from app.services.recommendation.scorer import (
    _benefit_score,
    _build_user_categories,
    _category_score,
    _freshness_score,
    _location_score,
    _profile_score,
    rank_schemes,
    score_scheme,
)
from app.services.recommendation.weights import (
    W_BENEFIT,
    W_CATEGORY,
    W_FRESHNESS,
    W_LOCATION,
    W_PROFILE,
)
from extensions import db as _db

# ══════════════════════════════════════════════════════════════════
# WEIGHT TESTS
# ══════════════════════════════════════════════════════════════════


class TestWeights:
    """Verify weight invariants."""

    def test_weights_sum_to_one(self):
        total = W_PROFILE + W_CATEGORY + W_LOCATION + W_FRESHNESS + W_BENEFIT
        assert abs(total - 1.0) < 1e-9

    def test_profile_is_largest_weight(self):
        assert W_PROFILE >= W_CATEGORY
        assert W_PROFILE >= W_LOCATION
        assert W_PROFILE >= W_FRESHNESS
        assert W_PROFILE >= W_BENEFIT


# ══════════════════════════════════════════════════════════════════
# COMPONENT SCORER TESTS
# ══════════════════════════════════════════════════════════════════


class TestProfileScore:
    """Tests for eligibility-based profile scoring."""

    def test_green_full_match(self):
        result = {
            "status": "green",
            "met": [{"field": "age"}, {"field": "income"}],
            "not_met": [],
            "missing": [],
        }
        score, reason = _profile_score(result)
        assert score >= 0.9
        assert "meets" in reason.lower()

    def test_amber_partial(self):
        result = {
            "status": "amber",
            "met": [{"field": "age"}],
            "not_met": [],
            "missing": [{"field": "income"}],
        }
        score, reason = _profile_score(result)
        assert 0.4 <= score <= 0.9
        assert "verification" in reason.lower() or "meets" in reason.lower()

    def test_red_no_match(self):
        result = {
            "status": "red",
            "met": [],
            "not_met": [{"field": "age"}, {"field": "state"}],
            "missing": [],
        }
        score, reason = _profile_score(result)
        assert score < 0.2
        assert "does not meet" in reason.lower()

    def test_no_rules(self):
        result = {"status": "green", "met": [], "not_met": [], "missing": []}
        score, _reason = _profile_score(result)
        assert score == 1.0


class TestCategoryScore:
    """Tests for category affinity scoring."""

    def test_full_overlap(self):
        score, reason = _category_score(["agriculture"], {"agriculture", "employment"})
        assert score >= 0.8
        assert "agriculture" in reason.lower()

    def test_no_overlap(self):
        score, _reason = _category_score(["housing"], {"education", "employment"})
        assert score <= 0.3

    def test_empty_scheme_categories(self):
        score, reason = _category_score([], {"agriculture"})
        assert score == 0.3
        assert "general" in reason.lower()

    def test_empty_user_categories(self):
        score, _reason = _category_score(["health"], set())
        assert score == 0.3

    def test_partial_overlap(self):
        score, _reason = _category_score(
            ["agriculture", "employment"], {"agriculture", "education"}
        )
        assert score >= 0.5


class TestLocationScore:
    """Tests for geographic relevance scoring."""

    def test_central_scheme(self):
        score, reason = _location_score("central", None, "Telangana")
        assert score == 0.8
        assert "nationwide" in reason.lower()

    def test_matching_state(self):
        score, _reason = _location_score("state", "Telangana", "Telangana")
        assert score == 1.0

    def test_different_state(self):
        score, reason = _location_score("state", "Kerala", "Telangana")
        assert score == 0.0
        assert "Kerala" in reason

    def test_no_user_state(self):
        score, reason = _location_score("state", "Telangana", None)
        assert score == 0.3
        assert "update" in reason.lower()

    def test_case_insensitive(self):
        score, _ = _location_score("state", "telangana", "Telangana")
        assert score == 1.0


class TestFreshnessScore:
    """Tests for verification recency scoring."""

    def test_verified_today(self):
        score, reason = _freshness_score(datetime.now(UTC))
        assert score == 1.0
        assert "today" in reason.lower()

    def test_verified_recently(self):
        recent = datetime.now(UTC) - timedelta(days=15)
        score, reason = _freshness_score(recent)
        assert score > 0.9
        assert "recently" in reason.lower()

    def test_verified_long_ago(self):
        old = datetime.now(UTC) - timedelta(days=400)
        score, _reason = _freshness_score(old)
        assert score <= 0.3

    def test_no_verification_date(self):
        score, reason = _freshness_score(None)
        assert score == 0.3
        assert "pending" in reason.lower()

    def test_naive_datetime_handled(self):
        naive = datetime(2025, 1, 1)
        score, _ = _freshness_score(naive)
        assert 0.0 <= score <= 1.0


class TestBenefitScore:
    """Tests for benefit amount scoring."""

    def test_high_benefit(self):
        score, reason = _benefit_score(500000)
        assert score == 1.0
        assert "₹" in reason

    def test_medium_benefit(self):
        score, reason = _benefit_score(50000)
        assert 0.0 < score < 1.0
        assert "₹" in reason

    def test_low_benefit(self):
        score, _reason = _benefit_score(1600)
        assert 0.0 < score < 0.1

    def test_no_benefit_amount(self):
        score, reason = _benefit_score(None)
        assert score == 0.5
        assert "varies" in reason.lower()

    def test_above_cap(self):
        score, _ = _benefit_score(1000000)
        assert score == 1.0


class TestUserCategories:
    """Tests for profile → category affinity derivation."""

    def test_farmer(self):
        cats = _build_user_categories({"occupation": "farmer"})
        assert "agriculture" in cats

    def test_student(self):
        cats = _build_user_categories({"occupation": "student"})
        assert "education" in cats

    def test_bpl_flag(self):
        cats = _build_user_categories({"is_bpl": True})
        assert "housing" in cats
        assert "social_security" in cats

    def test_female_gender(self):
        cats = _build_user_categories({"gender": "female"})
        assert "women" in cats

    def test_elderly(self):
        cats = _build_user_categories({"age": 60})
        assert "pension" in cats

    def test_education_level(self):
        cats = _build_user_categories({"education_level": "graduate"})
        assert "education" in cats

    def test_minority(self):
        cats = _build_user_categories({"is_minority": True})
        assert "minority" in cats

    def test_empty_profile(self):
        cats = _build_user_categories({})
        assert isinstance(cats, set)
        assert len(cats) == 0


# ══════════════════════════════════════════════════════════════════
# INTEGRATION: SCORE + RANK TESTS (with DB fixtures)
# ══════════════════════════════════════════════════════════════════


def _create_scheme(app, name, slug, level, state, categories, rules, benefit=None):
    """Helper to create a scheme with categories and rules."""
    scheme = Scheme(
        name=name,
        slug=slug,
        description=f"Test: {name}",
        benefits="Test benefits",
        level=level,
        state=state,
        verification_status="demo",
        is_active=True,
        max_benefit_amount=benefit,
    )
    _db.session.add(scheme)
    _db.session.flush()

    for cat in categories:
        _db.session.add(SchemeCategory(scheme_id=scheme.id, category=cat))

    _db.session.add(EligibilityRule(
        scheme_id=scheme.id,
        rules_json=rules,
        version=1,
        is_active=True,
    ))
    return scheme


class TestScoreScheme:
    """Integration test: score a full scheme model."""

    def test_score_returns_expected_keys(self, app):
        with app.app_context():
            scheme = _create_scheme(
                app, "Test Scheme", "test-score", "central", None,
                ["education"],
                {"op": "AND", "rules": [
                    {"field": "age", "cmp": "gte", "value": 18, "mandatory": True},
                ]},
                benefit=50000,
            )
            _db.session.commit()

            profile = {"age": 25, "occupation": "student"}
            result = score_scheme(scheme, profile)

            assert "scheme_id" in result
            assert "total_score" in result
            assert 0.0 <= result["total_score"] <= 1.0
            assert "eligibility_status" in result
            assert "components" in result
            assert "reasons" in result
            assert len(result["components"]) == 5

    def test_eligible_farmer_ranks_high_for_agri(self, app):
        with app.app_context():
            scheme = _create_scheme(
                app, "Farm Support", "farm-score", "central", None,
                ["agriculture"],
                {"op": "AND", "rules": [
                    {"field": "occupation", "cmp": "in",
                     "value": ["farmer"], "mandatory": True},
                ]},
                benefit=10000,
            )
            _db.session.commit()

            profile = {"occupation": "farmer", "state": "Telangana"}
            result = score_scheme(scheme, profile)
            assert result["eligibility_status"] == "green"
            assert result["total_score"] >= 0.5

    def test_ineligible_scores_low(self, app):
        with app.app_context():
            scheme = _create_scheme(
                app, "Women Only", "women-score", "state", "Kerala",
                ["women"],
                {"op": "AND", "rules": [
                    {"field": "gender", "cmp": "eq", "value": "female",
                     "mandatory": True},
                ]},
            )
            _db.session.commit()

            profile = {"gender": "male", "state": "Telangana"}
            result = score_scheme(scheme, profile)
            assert result["eligibility_status"] == "red"
            assert result["total_score"] < 0.3


class TestRankSchemes:
    """Integration test: rank multiple schemes."""

    def test_rank_sorts_green_before_red(self, app):
        with app.app_context():
            s1 = _create_scheme(
                app, "Green Scheme", "green-rank", "central", None,
                ["agriculture"],
                {"op": "AND", "rules": [
                    {"field": "age", "cmp": "gte", "value": 18, "mandatory": True},
                ]},
                benefit=50000,
            )
            s2 = _create_scheme(
                app, "Red Scheme", "red-rank", "state", "Kerala",
                ["women"],
                {"op": "AND", "rules": [
                    {"field": "gender", "cmp": "eq", "value": "female",
                     "mandatory": True},
                ]},
            )
            _db.session.commit()

            profile = {"age": 30, "gender": "male", "state": "Telangana"}
            ranked = rank_schemes([s1, s2], profile)

            assert ranked[0]["eligibility_status"] == "green"
            assert ranked[-1]["eligibility_status"] == "red"

    def test_exclude_red(self, app):
        with app.app_context():
            s1 = _create_scheme(
                app, "Open Scheme", "open-excl", "central", None,
                ["employment"],
                {"op": "AND", "rules": [
                    {"field": "age", "cmp": "gte", "value": 18, "mandatory": True},
                ]},
            )
            s2 = _create_scheme(
                app, "Closed Scheme", "closed-excl", "state", "Kerala",
                ["women"],
                {"op": "AND", "rules": [
                    {"field": "gender", "cmp": "eq", "value": "female",
                     "mandatory": True},
                ]},
            )
            _db.session.commit()

            profile = {"age": 30, "gender": "male"}
            ranked = rank_schemes([s1, s2], profile, exclude_red=True)

            assert all(r["eligibility_status"] != "red" for r in ranked)

    def test_limit_results(self, app):
        with app.app_context():
            schemes = []
            for i in range(5):
                s = _create_scheme(
                    app, f"Scheme {i}", f"limit-{i}", "central", None,
                    ["employment"],
                    {"op": "AND", "rules": [
                        {"field": "age", "cmp": "gte", "value": 18,
                         "mandatory": True},
                    ]},
                )
                schemes.append(s)
            _db.session.commit()

            profile = {"age": 25}
            ranked = rank_schemes(schemes, profile, limit=3)
            assert len(ranked) == 3

    def test_reasons_are_strings(self, app):
        with app.app_context():
            s = _create_scheme(
                app, "Reason Test", "reason-test", "central", None,
                ["education"],
                {"op": "AND", "rules": [
                    {"field": "age", "cmp": "gte", "value": 18, "mandatory": True},
                ]},
                benefit=100000,
            )
            _db.session.commit()

            profile = {"age": 25, "occupation": "student"}
            ranked = rank_schemes([s], profile)

            assert len(ranked) == 1
            assert isinstance(ranked[0]["reasons"], list)
            assert all(isinstance(r, str) for r in ranked[0]["reasons"])


# ══════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════


class TestRecommendAPI:
    """Tests for /api/v1/recommendations endpoints."""

    def _seed_profile(self, auth_client):
        """Update the test user's profile with meaningful data."""
        auth_client.put(
            "/api/v1/profile",
            json={
                "full_name": "Test Farmer",
                "gender": "male",
                "date_of_birth": "1990-05-15",
                "state": "Telangana",
                "occupation": "farmer",
                "annual_income": 100000,
                "is_bpl": True,
                "has_bank_account": True,
                "land_holding_acres": 2.0,
            },
        )

    def _seed_schemes(self, app):
        """Create a few schemes for recommendation testing."""
        with app.app_context():
            _create_scheme(
                app, "Farmer Support", "farmer-api", "central", None,
                ["agriculture"],
                {"op": "AND", "rules": [
                    {"field": "occupation", "cmp": "in",
                     "value": ["farmer"], "mandatory": True},
                    {"field": "has_bank_account", "cmp": "eq",
                     "value": True, "mandatory": True},
                ]},
                benefit=6000,
            )
            _create_scheme(
                app, "State Housing", "housing-api", "state", "Telangana",
                ["housing"],
                {"op": "AND", "rules": [
                    {"field": "is_bpl", "cmp": "eq",
                     "value": True, "mandatory": True},
                ]},
                benefit=120000,
            )
            _create_scheme(
                app, "Women Scheme", "women-api", "central", None,
                ["women"],
                {"op": "AND", "rules": [
                    {"field": "gender", "cmp": "eq",
                     "value": "female", "mandatory": True},
                ]},
                benefit=100000,
            )
            _db.session.commit()

    def test_get_recommendations(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        resp = auth_client.get("/api/v1/recommendations")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "total" in data
        assert "recommendations" in data
        assert data["total"] >= 1

        # First should be green (farmer matches farmer scheme)
        first = data["recommendations"][0]
        assert "scheme" in first
        assert "recommendation" in first
        assert first["recommendation"]["eligibility_status"] in ("green", "amber")

    def test_recommendations_unauthenticated(self, client):
        resp = client.get("/api/v1/recommendations")
        assert resp.status_code == 401

    def test_recommendations_no_profile(self, auth_client):
        # auth_client has a user but we didn't seed a profile with meaningful data
        # The registered user already has a profile from registration, so this test
        # verifies it still returns results (even with sparse profile)
        resp = auth_client.get("/api/v1/recommendations")
        assert resp.status_code == 200

    def test_recommendations_with_limit(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        resp = auth_client.get("/api/v1/recommendations?limit=1")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] <= 1

    def test_recommendations_exclude_red(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        resp = auth_client.get("/api/v1/recommendations?exclude_red=true")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        for rec in data["recommendations"]:
            assert rec["recommendation"]["eligibility_status"] != "red"

    def test_recommendations_filter_category(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        resp = auth_client.get("/api/v1/recommendations?category=agriculture")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        for rec in data["recommendations"]:
            assert "agriculture" in rec["scheme"]["categories"]

    def test_get_reasons_for_scheme(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        # Get scheme list first
        resp = auth_client.get("/api/v1/recommendations")
        recs = resp.get_json()["data"]["recommendations"]
        scheme_id = recs[0]["scheme"]["id"]

        # Get reasons
        resp = auth_client.get(f"/api/v1/recommendations/reasons/{scheme_id}")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "scheme" in data
        assert "scoring" in data
        assert "components" in data["scoring"]
        assert len(data["scoring"]["components"]) == 5

    def test_get_reasons_not_found(self, auth_client):
        self._seed_profile(auth_client)

        resp = auth_client.get("/api/v1/recommendations/reasons/99999")
        assert resp.status_code == 404

    def test_includes_profile_completion(self, auth_client, app):
        self._seed_profile(auth_client)
        self._seed_schemes(app)

        resp = auth_client.get("/api/v1/recommendations")
        data = resp.get_json()["data"]
        assert "profile_complete_pct" in data
        assert isinstance(data["profile_complete_pct"], int)
