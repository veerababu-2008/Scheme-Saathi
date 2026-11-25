"""SchemeSaathi AI — Recommendation routes.

Endpoints:
  GET /recommendations         Top scheme recommendations for the user
  GET /recommendations/reasons/<scheme_id>  Detailed scoring for one scheme
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from app.models.user import User
from app.models.scheme import Scheme, SchemeCategory
from app.schemas.recommend import RecommendQuerySchema
from app.services.eligibility.engine import build_profile_dict
from app.services.recommendation.scorer import rank_schemes, score_scheme
from app.utils import error_response, success_response

recommend_bp = Blueprint("recommend", __name__)


# ── GET /recommendations ─────────────────────────────────────────


@recommend_bp.route("", methods=["GET"])
@jwt_required()
def get_recommendations():
    """Return ranked scheme recommendations for the authenticated user."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.profile:
        return error_response(
            "PROFILE_INCOMPLETE",
            "Please complete your profile before getting recommendations.",
            status=400,
        )

    schema = RecommendQuerySchema()
    errors = schema.validate(request.args)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid parameters.", errors, 400)
    params = schema.load(request.args)

    # Build base query
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

    ranked = rank_schemes(
        schemes,
        profile_data,
        exclude_red=params.get("exclude_red", False),
        limit=params.get("limit", 10),
    )

    # Enrich with scheme details
    scheme_map = {s.id: s for s in schemes}
    results = []
    for rec in ranked:
        scheme = scheme_map.get(rec["scheme_id"])
        if not scheme:
            continue
        results.append({
            "scheme": scheme.to_list_dict(),
            "recommendation": {
                "score": rec["total_score"],
                "eligibility_status": rec["eligibility_status"],
                "eligibility_label": rec["eligibility_label"],
                "reasons": rec["reasons"],
                "components": rec["components"],
            },
        })

    return success_response({
        "total": len(results),
        "profile_complete_pct": user.profile.profile_complete_pct,
        "recommendations": results,
    })


# ── GET /recommendations/reasons/<scheme_id> ─────────────────────


@recommend_bp.route("/reasons/<int:scheme_id>", methods=["GET"])
@jwt_required()
def get_reasons(scheme_id):
    """Return detailed scoring breakdown for a single scheme."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.profile:
        return error_response(
            "PROFILE_INCOMPLETE",
            "Please complete your profile first.",
            status=400,
        )

    scheme = Scheme.query.filter_by(id=scheme_id, is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    profile_data = build_profile_dict(user.profile)
    result = score_scheme(scheme, profile_data)

    return success_response({
        "scheme": scheme.to_list_dict(),
        "scoring": result,
    })
