"""SchemeSaathi AI — Feedback routes.

Endpoints:
  POST /feedback         Submit feedback
  GET  /feedback         List own feedback (paginated)
  GET  /feedback/<id>    Get a single feedback entry
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.admin import Feedback
from app.models.scheme import Scheme
from app.schemas.feedback import FeedbackListSchema, SubmitFeedbackSchema
from app.utils import error_response, paginate_query, success_response
from extensions import db

feedback_bp = Blueprint("feedback", __name__)


# ── POST /feedback ───────────────────────────────────────────────


@feedback_bp.route("", methods=["POST"])
@jwt_required()
def submit_feedback():
    """Submit a feedback entry (bug, suggestion, or correction)."""
    schema = SubmitFeedbackSchema()
    payload = request.get_json(silent=True) or {}
    errors = schema.validate(payload)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(payload)
    user_id = int(get_jwt_identity())

    # Validate scheme_id if provided
    if data.get("scheme_id"):
        scheme = Scheme.query.filter_by(id=data["scheme_id"]).first()
        if not scheme:
            return error_response(
                "NOT_FOUND", "Referenced scheme not found.", status=404
            )

    fb = Feedback(
        user_id=user_id,
        scheme_id=data.get("scheme_id"),
        type=data["type"],
        message=data["message"],
    )
    db.session.add(fb)
    db.session.commit()

    return success_response(fb.to_dict(), status=201)


# ── GET /feedback ────────────────────────────────────────────────


@feedback_bp.route("", methods=["GET"])
@jwt_required()
def list_feedback():
    """List the authenticated user's feedback entries."""
    user_id = int(get_jwt_identity())
    schema = FeedbackListSchema()
    errors = schema.validate(request.args)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid parameters.", errors, 400)
    params = schema.load(request.args)

    query = Feedback.query.filter_by(user_id=user_id)
    if params.get("type"):
        query = query.filter_by(type=params["type"])

    query = query.order_by(Feedback.created_at.desc())
    items, meta = paginate_query(query, params["page"], params["per_page"])

    return success_response([fb.to_dict() for fb in items], meta)


# ── GET /feedback/<id> ───────────────────────────────────────────


@feedback_bp.route("/<int:feedback_id>", methods=["GET"])
@jwt_required()
def get_feedback(feedback_id):
    """Get a single feedback entry (own only)."""
    user_id = int(get_jwt_identity())
    fb = Feedback.query.filter_by(id=feedback_id, user_id=user_id).first()
    if not fb:
        return error_response("NOT_FOUND", "Feedback not found.", status=404)

    return success_response(fb.to_dict())
