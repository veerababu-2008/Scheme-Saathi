"""SchemeSaathi AI — Eligibility routes (check one, check all, history)."""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from app.models.user import User
from app.models.scheme import Scheme, SchemeCategory
from app.models.activity import EligibilityCheck
from app.schemas.eligibility import CheckAllQuerySchema
from app.services.eligibility.engine import (
    build_profile_dict,
    check_eligibility,
)
from app.services.eligibility.explain import build_explanation
from app.utils import error_response, paginate_query, success_response

eligibility_bp = Blueprint("eligibility", __name__)


# ── POST /check/<scheme_id> ──────────────────────────────────────


@eligibility_bp.route("/check/<int:scheme_id>", methods=["POST"])
@jwt_required()
def check_one(scheme_id):
    """Check eligibility for a single scheme."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.profile:
        return error_response(
            "PROFILE_INCOMPLETE",
            "Please create a profile before checking eligibility.",
            status=400,
        )

    scheme = Scheme.query.filter_by(id=scheme_id, is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    active_rule = scheme.active_rules
    rules_json = active_rule.rules_json if active_rule else None

    profile_data = build_profile_dict(user.profile)
    result = check_eligibility(rules_json, profile_data)
    explanation = build_explanation(result)

    # Persist the check
    check = EligibilityCheck(
        user_id=user.id,
        scheme_id=scheme.id,
        status=result["status"],
        result_json={
            "met": result["met"],
            "not_met": result["not_met"],
            "missing": result["missing"],
            "explanation": explanation,
        },
    )
    db.session.add(check)
    db.session.commit()

    return success_response({
        "scheme_id": scheme.id,
        "scheme_name": scheme.name,
        "scheme_slug": scheme.slug,
        "verification_status": scheme.verification_status,
        "eligibility": {
            "status": result["status"],
            "status_label": result["status_label"],
            "met": result["met"],
            "not_met": result["not_met"],
            "missing": result["missing"],
        },
        "explanation": explanation,
    })


# ── POST /check-all ──────────────────────────────────────────────


@eligibility_bp.route("/check-all", methods=["POST"])
@jwt_required()
def check_all():
    """Check eligibility against all active schemes."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.profile:
        return error_response(
            "PROFILE_INCOMPLETE",
            "Please create a profile before checking eligibility.",
            status=400,
        )

    # Optional filters
    schema = CheckAllQuerySchema()
    params = schema.load(request.args)

    query = Scheme.query.filter_by(is_active=True)
    if params.get("state"):
        query = query.filter(
            db.or_(Scheme.state == params["state"], Scheme.level == "central")
        )
    if params.get("level"):
        query = query.filter_by(level=params["level"])
    if params.get("category"):
        query = query.join(SchemeCategory).filter(
            SchemeCategory.category == params["category"]
        )

    schemes = query.all()
    profile_data = build_profile_dict(user.profile)

    results = []
    for scheme in schemes:
        active_rule = scheme.active_rules
        rules_json = active_rule.rules_json if active_rule else None
        result = check_eligibility(rules_json, profile_data)
        explanation = build_explanation(result)

        # Persist
        check = EligibilityCheck(
            user_id=user.id,
            scheme_id=scheme.id,
            status=result["status"],
            result_json={
                "met": result["met"],
                "not_met": result["not_met"],
                "missing": result["missing"],
            },
        )
        db.session.add(check)

        results.append({
            "scheme_id": scheme.id,
            "scheme_name": scheme.name,
            "scheme_slug": scheme.slug,
            "verification_status": scheme.verification_status,
            "eligibility": {
                "status": result["status"],
                "status_label": result["status_label"],
                "met_count": len(result["met"]),
                "not_met_count": len(result["not_met"]),
                "missing_count": len(result["missing"]),
            },
            "explanation_summary": explanation["summary"],
        })

    db.session.commit()

    # Sort: green first, then amber, then red
    order = {"green": 0, "amber": 1, "red": 2}
    results.sort(key=lambda r: order.get(r["eligibility"]["status"], 3))

    return success_response({
        "total_checked": len(results),
        "green_count": sum(1 for r in results if r["eligibility"]["status"] == "green"),
        "amber_count": sum(1 for r in results if r["eligibility"]["status"] == "amber"),
        "red_count": sum(1 for r in results if r["eligibility"]["status"] == "red"),
        "results": results,
    })


# ── GET /history ─────────────────────────────────────────────────


@eligibility_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    """Return past eligibility checks for the current user."""
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = (
        EligibilityCheck.query
        .filter_by(user_id=user_id)
        .order_by(EligibilityCheck.checked_at.desc())
    )
    items, meta = paginate_query(query, page, per_page)

    return success_response(
        [c.to_dict() for c in items],
        meta,
    )
