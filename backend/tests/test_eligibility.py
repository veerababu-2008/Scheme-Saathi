"""SchemeSaathi AI — Eligibility engine tests (30+ edge cases).

Tests are organised in four groups:
1. Operators       — every comparator, boundaries, type mismatches
2. Engine          — AND/OR tree logic, TRUE/FALSE/UNKNOWN propagation
3. Explanations    — human-readable output
4. API integration — /check and /check-all endpoints
"""

import pytest

from app.services.eligibility.operators import evaluate_operator
from app.services.eligibility.engine import check_eligibility
from app.services.eligibility.explain import build_explanation, explain_leaf


# ═══════════════════════════════════════════════════════════════════
# 1. OPERATORS (19 tests)
# ═══════════════════════════════════════════════════════════════════


class TestOperators:
    # ── eq ──
    def test_eq_match_string(self):
        assert evaluate_operator("eq", "farmer", "farmer") is True

    def test_eq_no_match(self):
        assert evaluate_operator("eq", "teacher", "farmer") is False

    def test_eq_match_bool(self):
        assert evaluate_operator("eq", True, True) is True

    def test_eq_bool_mismatch(self):
        assert evaluate_operator("eq", False, True) is False

    # ── neq ──
    def test_neq_match(self):
        assert evaluate_operator("neq", "teacher", "farmer") is True

    def test_neq_no_match(self):
        assert evaluate_operator("neq", "farmer", "farmer") is False

    # ── gt ──
    def test_gt_match(self):
        assert evaluate_operator("gt", 25, 18) is True

    def test_gt_no_match(self):
        assert evaluate_operator("gt", 15, 18) is False

    def test_gt_boundary_equal(self):
        assert evaluate_operator("gt", 18, 18) is False

    # ── gte ──
    def test_gte_match(self):
        assert evaluate_operator("gte", 25, 18) is True

    def test_gte_boundary(self):
        assert evaluate_operator("gte", 18, 18) is True

    # ── lt / lte ──
    def test_lt_match(self):
        assert evaluate_operator("lt", 100000, 250000) is True

    def test_lte_boundary(self):
        assert evaluate_operator("lte", 250000, 250000) is True

    def test_lte_fail(self):
        assert evaluate_operator("lte", 300000, 250000) is False

    # ── in ──
    def test_in_match(self):
        assert evaluate_operator("in", "farmer", ["farmer", "agri_labour"]) is True

    def test_in_no_match(self):
        assert evaluate_operator("in", "teacher", ["farmer", "agri_labour"]) is False

    # ── between ──
    def test_between_match(self):
        assert evaluate_operator("between", 25, [18, 40]) is True

    def test_between_lower_boundary(self):
        assert evaluate_operator("between", 18, [18, 40]) is True

    def test_between_upper_boundary(self):
        assert evaluate_operator("between", 40, [18, 40]) is True

    def test_between_out_below(self):
        assert evaluate_operator("between", 16, [18, 40]) is False

    def test_between_out_above(self):
        assert evaluate_operator("between", 45, [18, 40]) is False

    # ── unknown operator ──
    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError, match="Unknown comparator"):
            evaluate_operator("xor", 1, 2)


# ═══════════════════════════════════════════════════════════════════
# 2. ENGINE — three-valued logic (20 tests)
# ═══════════════════════════════════════════════════════════════════


def _leaf(field, cmp, value, mandatory=True):
    return {"field": field, "cmp": cmp, "value": value, "mandatory": mandatory}


def _and(*rules):
    return {"op": "AND", "rules": list(rules)}


def _or(*rules):
    return {"op": "OR", "rules": list(rules)}


class TestEngineSingleRule:
    def test_single_true(self):
        r = check_eligibility(
            _and(_leaf("age", "gte", 18)),
            {"age": 25},
        )
        assert r["status"] == "green"
        assert len(r["met"]) == 1
        assert len(r["not_met"]) == 0

    def test_single_false_mandatory(self):
        r = check_eligibility(
            _and(_leaf("age", "gte", 18, mandatory=True)),
            {"age": 15},
        )
        assert r["status"] == "red"
        assert len(r["not_met"]) == 1

    def test_single_false_non_mandatory(self):
        r = check_eligibility(
            _and(_leaf("age", "gte", 18, mandatory=False)),
            {"age": 15},
        )
        assert r["status"] == "amber"

    def test_single_unknown(self):
        r = check_eligibility(
            _and(_leaf("age", "gte", 18)),
            {},
        )
        assert r["status"] == "amber"
        assert len(r["missing"]) == 1


class TestEngineAND:
    def test_and_all_true(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18),
                _leaf("annual_income", "lte", 250000),
            ),
            {"age": 25, "annual_income": 150000},
        )
        assert r["status"] == "green"
        assert len(r["met"]) == 2

    def test_and_one_mandatory_false_is_red(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18, mandatory=True),
                _leaf("annual_income", "lte", 250000, mandatory=True),
            ),
            {"age": 25, "annual_income": 500000},
        )
        assert r["status"] == "red"

    def test_and_one_non_mandatory_false_is_amber(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18, mandatory=True),
                _leaf("is_bpl", "eq", True, mandatory=False),
            ),
            {"age": 25, "is_bpl": False},
        )
        assert r["status"] == "amber"

    def test_and_one_unknown_is_amber(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18),
                _leaf("annual_income", "lte", 250000),
            ),
            {"age": 25},  # income missing
        )
        assert r["status"] == "amber"
        assert len(r["missing"]) == 1
        assert len(r["met"]) == 1


class TestEngineOR:
    def test_or_one_true_is_green(self):
        r = check_eligibility(
            _or(
                _leaf("occupation", "in", ["farmer", "agri_labour"]),
                _leaf("category", "in", ["SC", "ST"]),
            ),
            {"occupation": "farmer", "category": "General"},
        )
        assert r["status"] == "green"
        assert len(r["met"]) == 1
        assert len(r["not_met"]) == 1  # category didn't match but OR passed

    def test_or_all_false_mandatory_is_red(self):
        r = check_eligibility(
            _or(
                _leaf("occupation", "in", ["farmer"], mandatory=True),
                _leaf("category", "in", ["SC", "ST"], mandatory=True),
            ),
            {"occupation": "teacher", "category": "General"},
        )
        assert r["status"] == "red"

    def test_or_all_false_non_mandatory_is_amber(self):
        r = check_eligibility(
            _or(
                _leaf("occupation", "in", ["farmer"], mandatory=False),
                _leaf("category", "in", ["SC", "ST"], mandatory=False),
            ),
            {"occupation": "teacher", "category": "General"},
        )
        assert r["status"] == "amber"

    def test_or_with_unknown_no_true(self):
        r = check_eligibility(
            _or(
                _leaf("occupation", "in", ["farmer"]),
                _leaf("category", "in", ["SC", "ST"]),
            ),
            {"occupation": "teacher"},  # category missing
        )
        assert r["status"] == "amber"  # UNKNOWN propagates


class TestEngineNested:
    def test_nested_and_or(self):
        """AND(age >= 18, OR(farmer, SC/ST))"""
        rules = _and(
            _leaf("age", "gte", 18, mandatory=True),
            _or(
                _leaf("occupation", "in", ["farmer", "agri_labour"]),
                _leaf("category", "in", ["SC", "ST"]),
            ),
        )
        profile = {"age": 25, "occupation": "farmer", "category": "General"}
        r = check_eligibility(rules, profile)
        assert r["status"] == "green"

    def test_nested_and_or_fails_or(self):
        """AND(age >= 18, OR(farmer, SC/ST)) — OR fails"""
        rules = _and(
            _leaf("age", "gte", 18, mandatory=True),
            _or(
                _leaf("occupation", "in", ["farmer"], mandatory=True),
                _leaf("category", "in", ["SC", "ST"], mandatory=True),
            ),
        )
        profile = {"age": 25, "occupation": "teacher", "category": "General"}
        r = check_eligibility(rules, profile)
        assert r["status"] == "red"

    def test_deeply_nested(self):
        """AND(age, OR(AND(state, occupation), category))"""
        rules = _and(
            _leaf("age", "gte", 18),
            _or(
                _and(
                    _leaf("state", "eq", "Telangana"),
                    _leaf("occupation", "in", ["farmer"]),
                ),
                _leaf("category", "in", ["SC", "ST"]),
            ),
        )
        profile = {"age": 30, "state": "Telangana", "occupation": "farmer", "category": "OBC"}
        r = check_eligibility(rules, profile)
        assert r["status"] == "green"


class TestEngineEdgeCases:
    def test_empty_rules_is_green(self):
        r = check_eligibility({}, {"age": 25})
        assert r["status"] == "green"

    def test_none_rules_is_green(self):
        r = check_eligibility(None, {"age": 25})
        assert r["status"] == "green"

    def test_rules_with_empty_children(self):
        r = check_eligibility({"op": "AND", "rules": []}, {"age": 25})
        assert r["status"] == "green"

    def test_all_fields_missing_is_amber(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18),
                _leaf("annual_income", "lte", 250000),
                _leaf("occupation", "in", ["farmer"]),
            ),
            {},
        )
        assert r["status"] == "amber"
        assert len(r["missing"]) == 3

    def test_boolean_field(self):
        r = check_eligibility(
            _and(_leaf("has_bank_account", "eq", True)),
            {"has_bank_account": True},
        )
        assert r["status"] == "green"

    def test_income_lte_exact_boundary(self):
        r = check_eligibility(
            _and(_leaf("annual_income", "lte", 250000, mandatory=True)),
            {"annual_income": 250000},
        )
        assert r["status"] == "green"

    def test_income_lte_one_over(self):
        r = check_eligibility(
            _and(_leaf("annual_income", "lte", 250000, mandatory=True)),
            {"annual_income": 250001},
        )
        assert r["status"] == "red"

    def test_between_age(self):
        r = check_eligibility(
            _and(_leaf("age", "between", [18, 40])),
            {"age": 30},
        )
        assert r["status"] == "green"

    def test_land_holding_gt_zero(self):
        r = check_eligibility(
            _and(_leaf("land_holding_acres", "gt", 0, mandatory=True)),
            {"land_holding_acres": 2.5},
        )
        assert r["status"] == "green"

    def test_land_holding_zero_fails(self):
        r = check_eligibility(
            _and(_leaf("land_holding_acres", "gt", 0, mandatory=True)),
            {"land_holding_acres": 0},
        )
        assert r["status"] == "red"

    def test_met_not_met_missing_counts(self):
        r = check_eligibility(
            _and(
                _leaf("age", "gte", 18, mandatory=True),
                _leaf("annual_income", "lte", 250000, mandatory=True),
                _leaf("is_bpl", "eq", True, mandatory=False),
            ),
            {"age": 25},  # income and is_bpl missing
        )
        assert len(r["met"]) == 1
        assert len(r["not_met"]) == 0
        assert len(r["missing"]) == 2

    def test_source_id_passthrough(self):
        """source_id from the rule should appear in the detail dict."""
        rule = {"field": "age", "cmp": "gte", "value": 18,
                "mandatory": True, "source_id": 42}
        r = check_eligibility({"op": "AND", "rules": [rule]}, {"age": 25})
        assert r["met"][0]["source_id"] == 42


# ═══════════════════════════════════════════════════════════════════
# 3. EXPLANATIONS (5 tests)
# ═══════════════════════════════════════════════════════════════════


class TestExplanations:
    def test_met_explanation_format(self):
        detail = {
            "field": "age", "cmp": "gte", "expected": 18,
            "actual": 25, "mandatory": True, "result": "TRUE",
        }
        text = explain_leaf(detail)
        assert "✓" in text
        assert "25" in text
        assert "18" in text

    def test_not_met_explanation_format(self):
        detail = {
            "field": "annual_income", "cmp": "lte", "expected": 250000,
            "actual": 500000, "mandatory": True, "result": "FALSE",
        }
        text = explain_leaf(detail)
        assert "✗" in text
        assert "₹" in text

    def test_missing_explanation_format(self):
        detail = {
            "field": "occupation", "cmp": "in", "expected": ["farmer"],
            "actual": None, "mandatory": True, "result": "UNKNOWN",
        }
        text = explain_leaf(detail)
        assert "⚠" in text
        assert "not provided" in text

    def test_full_explanation_green(self):
        result = check_eligibility(
            _and(_leaf("age", "gte", 18)),
            {"age": 25},
        )
        exp = build_explanation(result)
        assert exp["status"] == "green"
        assert "potentially eligible" in exp["summary"].lower()
        assert len(exp["details"]) == 1

    def test_full_explanation_red(self):
        result = check_eligibility(
            _and(_leaf("age", "gte", 18, mandatory=True)),
            {"age": 10},
        )
        exp = build_explanation(result)
        assert exp["status"] == "red"
        assert "do not appear to meet" in exp["summary"].lower()


# ═══════════════════════════════════════════════════════════════════
# 4. API INTEGRATION (8 tests)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture()
def user_with_profile(auth_client):
    """Authenticated client with a full farmer profile."""
    auth_client.put("/api/v1/profile/", json={
        "full_name": "Test Farmer",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "state": "Telangana",
        "district": "Rangareddy",
        "pincode": "500032",
        "category": "OBC",
        "occupation": "farmer",
        "education_level": "secondary",
        "annual_income": 120000,
        "is_bpl": True,
        "is_differently_abled": False,
        "marital_status": "married",
        "num_dependents": 3,
        "land_holding_acres": 2.5,
        "has_bank_account": True,
    })
    return auth_client


class TestEligibilityAPI:
    def test_check_single_scheme(self, user_with_profile, seeded_schemes, app):
        """Check eligibility for a known test scheme."""
        with app.app_context():
            from app.models.scheme import Scheme
            scheme = Scheme.query.filter_by(slug="test-education").first()
            resp = user_with_profile.post(f"/api/v1/eligibility/check/{scheme.id}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["eligibility"]["status"] in ("green", "amber", "red")
        assert "explanation" in body["data"]

    def test_check_all_schemes(self, user_with_profile, seeded_schemes):
        resp = user_with_profile.post("/api/v1/eligibility/check-all")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["total_checked"] == 5
        assert "green_count" in body["data"]
        assert "amber_count" in body["data"]
        assert "red_count" in body["data"]
        # Results should be sorted: green first
        statuses = [r["eligibility"]["status"] for r in body["data"]["results"]]
        order = {"green": 0, "amber": 1, "red": 2}
        assert statuses == sorted(statuses, key=lambda s: order[s])

    def test_check_nonexistent_scheme(self, user_with_profile):
        resp = user_with_profile.post("/api/v1/eligibility/check/99999")
        assert resp.status_code == 404

    def test_check_unauthenticated(self, client, seeded_schemes):
        resp = client.post("/api/v1/eligibility/check/1")
        assert resp.status_code == 401

    def test_check_no_profile(self, client):
        """Register but do NOT create a profile → should fail gracefully."""
        client.post("/api/v1/auth/register", json={
            "email": "noprofile@example.com",
            "password": "GoodPass1234",
        })
        resp = client.post("/api/v1/eligibility/check/1")
        # Should succeed since register creates a profile,
        # but with mostly-UNKNOWN results
        assert resp.status_code in (200, 400, 404)

    def test_history_endpoint(self, user_with_profile, seeded_schemes, app):
        # Run a check first
        with app.app_context():
            from app.models.scheme import Scheme
            scheme = Scheme.query.filter_by(slug="test-education").first()
            user_with_profile.post(f"/api/v1/eligibility/check/{scheme.id}")
        # Now get history
        resp = user_with_profile.get("/api/v1/eligibility/history")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) >= 1

    def test_check_all_with_state_filter(self, user_with_profile, seeded_schemes):
        resp = user_with_profile.post(
            "/api/v1/eligibility/check-all?state=Telangana"
        )
        assert resp.status_code == 200
        body = resp.get_json()
        # Should include central + Telangana state schemes
        assert body["data"]["total_checked"] >= 3

    def test_check_scheme_stores_result(self, user_with_profile, seeded_schemes, app):
        """Verify the check is persisted to the database."""
        with app.app_context():
            from app.models.scheme import Scheme
            from app.models.activity import EligibilityCheck
            scheme = Scheme.query.filter_by(slug="test-health").first()
            user_with_profile.post(f"/api/v1/eligibility/check/{scheme.id}")
            checks = EligibilityCheck.query.filter_by(scheme_id=scheme.id).all()
            assert len(checks) >= 1
            assert checks[0].status in ("green", "amber", "red")
