"""SchemeSaathi AI — Profile routes (get, update, completion, export, delete)."""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from app.models.user import User, UserProfile
from app.schemas.profile import ProfileUpdateSchema
from app.utils import error_response, success_response

profile_bp = Blueprint("profile", __name__)


# ── GET / ────────────────────────────────────────────────────────


@profile_bp.route("/", methods=["GET"])
@jwt_required()
def get_profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.is_active:
        return error_response("NOT_FOUND", "User not found.", status=404)

    profile = user.profile
    if not profile:
        return error_response("NOT_FOUND", "Profile not found.", status=404)

    return success_response(profile.to_dict())


# ── PUT / ────────────────────────────────────────────────────────


@profile_bp.route("/", methods=["PUT"])
@jwt_required()
def update_profile():
    schema = ProfileUpdateSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.json)
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.is_active:
        return error_response("NOT_FOUND", "User not found.", status=404)

    profile = user.profile
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)

    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)

    db.session.commit()
    return success_response(profile.to_dict())


# ── GET /completion ──────────────────────────────────────────────


@profile_bp.route("/completion", methods=["GET"])
@jwt_required()
def profile_completion():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.profile:
        return success_response({"profile_complete_pct": 0})

    profile = user.profile
    missing = [
        f for f in profile._PROFILE_FIELDS
        if getattr(profile, f) in (None, "")
    ]

    return success_response({
        "profile_complete_pct": profile.profile_complete_pct,
        "missing_fields": missing,
        "total_fields": len(profile._PROFILE_FIELDS),
        "filled_fields": len(profile._PROFILE_FIELDS) - len(missing),
    })


# ── POST /export ─────────────────────────────────────────────────


@profile_bp.route("/export", methods=["POST"])
@jwt_required()
def export_data():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return error_response("NOT_FOUND", "User not found.", status=404)

    export = {
        "user": user.to_dict(),
        "profile": user.profile.to_dict() if user.profile else None,
        "saved_schemes": [s.to_dict() for s in user.saved_schemes],
        "eligibility_checks": [c.to_dict() for c in user.eligibility_checks],
        "chat_sessions": [
            s.to_dict(include_messages=True) for s in user.chat_sessions
        ],
    }
    return success_response(export)


# ── DELETE /account ──────────────────────────────────────────────


@profile_bp.route("/account", methods=["DELETE"])
@jwt_required()
def delete_account():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return error_response("NOT_FOUND", "User not found.", status=404)

    # Hard delete — cascades remove all related records
    db.session.delete(user)
    db.session.commit()

    return success_response({"message": "Account and all data deleted."})
