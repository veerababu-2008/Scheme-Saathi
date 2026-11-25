"""SchemeSaathi AI — Application factory."""

import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    config_name = config_name or os.getenv("FLASK_ENV", "development")
    from config import config_map

    app.config.from_object(config_map[config_name])

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)
    _configure_jwt()

    return app


# ── Extension wiring ─────────────────────────────────────────────


def _init_extensions(app):
    from extensions import cors, db, jwt, limiter, migrate

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    limiter.init_app(app)

    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    cors.init_app(app, origins=origins, supports_credentials=True)


# ── Blueprint registration ───────────────────────────────────────


def _register_blueprints(app):
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.checklist import checklist_bp
    from app.routes.eligibility import eligibility_bp
    from app.routes.feedback import feedback_bp
    from app.routes.profile import profile_bp
    from app.routes.recommend import recommend_bp
    from app.routes.saved import saved_bp
    from app.routes.schemes import schemes_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(profile_bp, url_prefix="/api/v1/profile")
    app.register_blueprint(schemes_bp, url_prefix="/api/v1/schemes")
    app.register_blueprint(eligibility_bp, url_prefix="/api/v1/eligibility")
    app.register_blueprint(chat_bp, url_prefix="/api/v1/chat")
    app.register_blueprint(recommend_bp, url_prefix="/api/v1/recommendations")
    app.register_blueprint(saved_bp, url_prefix="/api/v1/saved")
    app.register_blueprint(checklist_bp, url_prefix="/api/v1/checklist")
    app.register_blueprint(feedback_bp, url_prefix="/api/v1/feedback")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")


# ── Error handlers (consistent JSON shape) ───────────────────────


def _register_error_handlers(app):
    from marshmallow import ValidationError

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input.",
                    "details": exc.messages,
                },
            ),
            400,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": exc.name.upper().replace(" ", "_"),
                    "message": exc.description,
                    "details": None,
                },
            ),
            exc.code,
        )

    @app.errorhandler(429)
    def handle_rate_limit(_exc):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please try again later.",
                    "details": None,
                },
            ),
            429,
        )

    @app.errorhandler(500)
    def handle_internal(_exc):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": None,
                },
            ),
            500,
        )


# ── CLI commands ─────────────────────────────────────────────────


def _register_cli(app):
    from seeds.seed_runner import register_seed_commands

    register_seed_commands(app)


# ── JWT callbacks ────────────────────────────────────────────────


def _configure_jwt():
    from app.models.user import TokenBlocklist
    from extensions import db, jwt

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return (
            db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
            is not None
        )

    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": "TOKEN_EXPIRED",
                    "message": "Your session has expired. Please log in again.",
                    "details": None,
                },
            ),
            401,
        )

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return (
            jsonify(
                data=None,
                meta=None,
                error={
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required.",
                    "details": reason,
                },
            ),
            401,
        )
