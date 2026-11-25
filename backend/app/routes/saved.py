"""SchemeSaathi AI — Saved schemes (bookmarks) routes.

Endpoints:
  POST   /saved              Bookmark a scheme
  GET    /saved              List bookmarked schemes
  PATCH  /saved/<id>         Update bookmark notes
  DELETE /saved/<id>         Remove bookmark
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from app.models.scheme import Scheme
from app.models.activity import SavedScheme
from app.schemas.saved import SaveSchemeSchema, UpdateNotesSchema, SavedListSchema
from app.utils import error_response, paginate_query, success_response

saved_bp = Blueprint("saved", __name__)


# ── POST /saved ──────────────────────────────────────────────────


@saved_bp.route("", methods=["POST"])
@jwt_required()
def save_scheme():
    """Bookmark a scheme."""
    schema = SaveSchemeSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.get_json())
    user_id = int(get_jwt_identity())

    scheme = Scheme.query.filter_by(id=data["scheme_id"], is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    existing = SavedScheme.query.filter_by(
        user_id=user_id, scheme_id=scheme.id
    ).first()
    if existing:
        return error_response(
            "ALREADY_SAVED", "Scheme is already bookmarked.", status=409
        )

    saved = SavedScheme(
        user_id=user_id,
        scheme_id=scheme.id,
        notes=data.get("notes"),
    )
    db.session.add(saved)
    db.session.commit()

    return success_response(
        {
            **saved.to_dict(),
            "scheme": scheme.to_list_dict(),
        },
        status=201,
    )


# ── GET /saved ───────────────────────────────────────────────────


@saved_bp.route("", methods=["GET"])
@jwt_required()
def list_saved():
    """List the authenticated user's bookmarked schemes."""
    user_id = int(get_jwt_identity())
    schema = SavedListSchema()
    params = schema.load(request.args)

    query = (
        SavedScheme.query
        .filter_by(user_id=user_id)
        .order_by(SavedScheme.saved_at.desc())
    )
    items, meta = paginate_query(query, params["page"], params["per_page"])

    results = []
    for saved in items:
        entry = saved.to_dict()
        if saved.scheme:
            entry["scheme"] = saved.scheme.to_list_dict()
        results.append(entry)

    return success_response(results, meta)


# ── PATCH /saved/<id> ────────────────────────────────────────────


@saved_bp.route("/<int:saved_id>", methods=["PATCH"])
@jwt_required()
def update_notes(saved_id):
    """Update the notes on a bookmarked scheme."""
    user_id = int(get_jwt_identity())
    saved = SavedScheme.query.filter_by(id=saved_id, user_id=user_id).first()
    if not saved:
        return error_response("NOT_FOUND", "Bookmark not found.", status=404)

    schema = UpdateNotesSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.get_json())
    saved.notes = data["notes"]
    db.session.commit()

    return success_response(saved.to_dict())


# ── DELETE /saved/<id> ───────────────────────────────────────────


@saved_bp.route("/<int:saved_id>", methods=["DELETE"])
@jwt_required()
def unsave_scheme(saved_id):
    """Remove a bookmark."""
    user_id = int(get_jwt_identity())
    saved = SavedScheme.query.filter_by(id=saved_id, user_id=user_id).first()
    if not saved:
        return error_response("NOT_FOUND", "Bookmark not found.", status=404)

    db.session.delete(saved)
    db.session.commit()

    return success_response({"deleted": saved_id})
