"""SchemeSaathi AI — Auth routes (register, login, logout, refresh, password)."""

from datetime import UTC, datetime

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from app.models.user import TokenBlocklist, User, UserProfile
from app.schemas.auth import LoginSchema, PasswordChangeSchema, RegisterSchema
from app.utils import error_response, success_response
from extensions import db, limiter

auth_bp = Blueprint("auth", __name__)


# ── POST /register ───────────────────────────────────────────────


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5/minute")
def register():
    schema = RegisterSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.json)

    if User.query.filter_by(email=data["email"]).first():
        return error_response("CONFLICT", "Email already registered.", status=409)

    user = User(email=data["email"], role="citizen")
    user.set_password(data["password"])

    profile = UserProfile(user=user, full_name=data.get("full_name", ""))

    db.session.add(user)
    db.session.add(profile)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    resp, status = success_response(
        {"user_id": user.id, "email": user.email}, status=201
    )
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, status


# ── POST /login ──────────────────────────────────────────────────


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    schema = LoginSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.json)
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not user.is_active or not user.check_password(data["password"]):
        return error_response(
            "UNAUTHORIZED", "Invalid email or password.", status=401
        )

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    resp, status = success_response({
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "profile_complete_pct": (
            user.profile.profile_complete_pct if user.profile else 0
        ),
    })
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, status


# ── POST /logout ─────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    db.session.add(TokenBlocklist(jti=jti, created_at=datetime.now(UTC)))
    db.session.commit()

    resp, status = success_response({"message": "Logged out successfully."})
    unset_jwt_cookies(resp)
    return resp, status


# ── POST /refresh ────────────────────────────────────────────────


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    resp, status = success_response({"message": "Token refreshed."})
    set_access_cookies(resp, access_token)
    return resp, status


# ── PUT /password ────────────────────────────────────────────────


@auth_bp.route("/password", methods=["PUT"])
@jwt_required()
@limiter.limit("5/minute")
def change_password():
    schema = PasswordChangeSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.json)
    user = db.session.get(User, int(get_jwt_identity()))

    if not user or not user.check_password(data["current_password"]):
        return error_response(
            "UNAUTHORIZED", "Current password is incorrect.", status=401
        )

    user.set_password(data["new_password"])
    db.session.commit()

    return success_response({"message": "Password changed successfully."})
