"""SchemeSaathi AI — Admin routes and role-based access control.

Endpoints:
  POST   /login                 Admin login
  GET    /me                    Current admin profile
  GET    /schemes               List schemes with admin filters
  POST   /schemes               Create new scheme
  GET    /schemes/<id>          Get detailed scheme
  PUT    /schemes/<id>          Update scheme
  DELETE /schemes/<id>          Delete/deactivate scheme
  GET    /schemes/<id>/rules    List rule versions
  POST   /schemes/<id>/rules    Add new rule version
  GET    /feedback              List all feedback
  PATCH  /feedback/<id>         Update feedback status
  GET    /audit-logs            Query audit logs
  GET    /analytics             Platform metrics & statistics
"""

import re
from functools import wraps
from flask import Blueprint, g, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
)
from sqlalchemy import func

from extensions import db
from app.models.admin import AdminUser, AuditLog, Feedback
from app.models.activity import EligibilityCheck, SavedScheme
from app.models.scheme import (
    EligibilityRule,
    Scheme,
    SchemeCategory,
    SchemeDocument,
    SchemeSource,
)
from app.models.user import User
from app.schemas.admin import (
    AdminFeedbackUpdateSchema,
    AdminListQuerySchema,
    AdminLoginSchema,
    AdminRuleCreateSchema,
    AdminSchemeCreateSchema,
    AdminSchemeUpdateSchema,
)
from app.utils import error_response, paginate_query, success_response

admin_bp = Blueprint("admin", __name__)


# ── RBAC & Audit Helpers ──────────────────────────────────────────


def admin_required(roles=None):
    """Enforce admin JWT authentication and optional role restrictions."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if not claims.get("is_admin"):
                return error_response(
                    "FORBIDDEN", "Admin privileges required.", status=403
                )
            admin_id = int(get_jwt_identity())
            admin = db.session.get(AdminUser, admin_id)
            if not admin or not admin.is_active:
                return error_response(
                    "UNAUTHORIZED", "Admin account inactive or not found.", status=401
                )
            if roles and admin.role not in roles:
                return error_response(
                    "FORBIDDEN",
                    f"Action requires one of roles: {', '.join(roles)}.",
                    status=403,
                )
            g.current_admin = admin
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def log_audit(admin_id, action, entity_type, entity_id=None, diff_json=None):
    """Record an administrative action to the AuditLog table."""
    audit = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        diff_json=diff_json,
        ip_address=request.remote_addr,
    )
    db.session.add(audit)


# ── Admin Auth ───────────────────────────────────────────────────


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    schema = AdminLoginSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.get_json())
    admin = AdminUser.query.filter_by(email=data["email"]).first()
    if not admin or not admin.is_active or not admin.check_password(data["password"]):
        return error_response(
            "UNAUTHORIZED", "Invalid admin email or password.", status=401
        )

    claims = {"is_admin": True, "admin_role": admin.role}
    access_token = create_access_token(identity=str(admin.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(admin.id), additional_claims=claims)

    resp, status = success_response({"admin": admin.to_dict()})
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, status


@admin_bp.route("/me", methods=["GET"])
@admin_required()
def admin_me():
    return success_response({"admin": g.current_admin.to_dict()})


# ── Scheme Management ────────────────────────────────────────────


@admin_bp.route("/schemes", methods=["GET"])
@admin_required()
def admin_list_schemes():
    schema = AdminListQuerySchema()
    args = schema.load(request.args)
    q = Scheme.query

    if args.get("search"):
        term = f"%{args['search']}%"
        q = q.filter((Scheme.name.ilike(term)) | (Scheme.slug.ilike(term)))
    if args.get("status"):
        q = q.filter(Scheme.verification_status == args["status"])
    if args.get("level"):
        q = q.filter(Scheme.level == args["level"])
    if args.get("state"):
        q = q.filter(Scheme.state == args["state"])
    if args.get("category"):
        q = q.join(SchemeCategory).filter(SchemeCategory.category == args["category"])

    items, meta = paginate_query(
        q.order_by(Scheme.id.desc()), args["page"], args["per_page"]
    )
    return success_response([s.to_dict(include_rules=True) for s in items], meta=meta)


@admin_bp.route("/schemes", methods=["POST"])
@admin_required(roles=["super", "editor"])
def admin_create_scheme():
    schema = AdminSchemeCreateSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid scheme data.", errors, 400)

    data = schema.load(request.get_json())
    slug = data.get("slug") or re.sub(r"[^a-z0-9]+", "-", data["name"].lower()).strip("-")
    if Scheme.query.filter_by(slug=slug).first():
        return error_response("CONFLICT", f"Slug '{slug}' already exists.", status=409)

    scheme = Scheme(
        name=data["name"],
        name_te=data.get("name_te"),
        name_hi=data.get("name_hi"),
        slug=slug,
        description=data["description"],
        description_te=data.get("description_te"),
        description_hi=data.get("description_hi"),
        benefits=data["benefits"],
        benefits_te=data.get("benefits_te"),
        benefits_hi=data.get("benefits_hi"),
        level=data.get("level", "central"),
        state=data.get("state"),
        department=data.get("department"),
        ministry=data.get("ministry"),
        apply_url=data.get("apply_url"),
        official_url=data.get("official_url"),
        verification_status=data.get("verification_status", "pending"),
        is_active=data.get("is_active", True),
        deadline=data.get("deadline"),
        max_benefit_amount=data.get("max_benefit_amount"),
    )
    db.session.add(scheme)
    db.session.flush()

    for cat in data.get("categories") or []:
        db.session.add(SchemeCategory(scheme_id=scheme.id, category=cat))
    for doc in data.get("documents") or []:
        db.session.add(SchemeDocument(
            scheme_id=scheme.id,
            document_name=doc.get("document_name", ""),
            document_name_te=doc.get("document_name_te"),
            document_name_hi=doc.get("document_name_hi"),
            is_mandatory=doc.get("is_mandatory", True),
            description=doc.get("description"),
        ))
    for src in data.get("sources") or []:
        db.session.add(SchemeSource(
            scheme_id=scheme.id,
            title=src.get("title", ""),
            url=src.get("url"),
            source_type=src.get("source_type", "url"),
            is_primary=src.get("is_primary", False),
        ))

    log_audit(g.current_admin.id, "create_scheme", "scheme", scheme.id, {"slug": slug})
    db.session.commit()
    return success_response(scheme.to_dict(include_rules=True), status=201)


@admin_bp.route("/schemes/<int:scheme_id>", methods=["GET"])
@admin_required()
def admin_get_scheme(scheme_id):
    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)
    return success_response(scheme.to_dict(include_rules=True))


@admin_bp.route("/schemes/<int:scheme_id>", methods=["PUT"])
@admin_required(roles=["super", "editor"])
def admin_update_scheme(scheme_id):
    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    schema = AdminSchemeUpdateSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid update payload.", errors, 400)

    data = schema.load(request.get_json())
    diff = {}
    for key, value in data.items():
        if key == "categories":
            SchemeCategory.query.filter_by(scheme_id=scheme.id).delete()
            for cat in value:
                db.session.add(SchemeCategory(scheme_id=scheme.id, category=cat))
            diff["categories"] = value
        elif hasattr(scheme, key):
            old = getattr(scheme, key)
            if old != value:
                diff[key] = {"old": str(old), "new": str(value)}
                setattr(scheme, key, value)

    log_audit(g.current_admin.id, "update_scheme", "scheme", scheme.id, diff)
    db.session.commit()
    return success_response(scheme.to_dict(include_rules=True))


@admin_bp.route("/schemes/<int:scheme_id>", methods=["DELETE"])
@admin_required(roles=["super"])
def admin_delete_scheme(scheme_id):
    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    hard = request.args.get("hard", "false").lower() == "true"
    if hard:
        db.session.delete(scheme)
        log_audit(g.current_admin.id, "hard_delete_scheme", "scheme", scheme_id)
    else:
        scheme.is_active = False
        log_audit(g.current_admin.id, "deactivate_scheme", "scheme", scheme_id)

    db.session.commit()
    return success_response({"deleted": True, "hard": hard, "id": scheme_id})


# ── Eligibility Rule Versioning ──────────────────────────────────


@admin_bp.route("/schemes/<int:scheme_id>/rules", methods=["GET"])
@admin_required()
def admin_list_rules(scheme_id):
    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)
    rules = (
        EligibilityRule.query.filter_by(scheme_id=scheme_id)
        .order_by(EligibilityRule.version.desc())
        .all()
    )
    return success_response([r.to_dict() for r in rules])


@admin_bp.route("/schemes/<int:scheme_id>/rules", methods=["POST"])
@admin_required(roles=["super", "editor"])
def admin_create_rule(scheme_id):
    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    schema = AdminRuleCreateSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid rule data.", errors, 400)

    data = schema.load(request.get_json())
    # Deactivate prior rules
    EligibilityRule.query.filter_by(scheme_id=scheme_id).update({"is_active": False})

    latest = (
        EligibilityRule.query.filter_by(scheme_id=scheme_id)
        .order_by(EligibilityRule.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1

    rule = EligibilityRule(
        scheme_id=scheme_id,
        rules_json=data["rules_json"],
        version=next_version,
        is_active=True,
        notes=data.get("notes"),
    )
    db.session.add(rule)
    db.session.flush()

    log_audit(
        g.current_admin.id,
        "create_rule",
        "eligibility_rule",
        rule.id,
        {"scheme_id": scheme_id, "version": next_version},
    )
    db.session.commit()
    return success_response(rule.to_dict(), status=201)


# ── Feedback Moderation ──────────────────────────────────────────


@admin_bp.route("/feedback", methods=["GET"])
@admin_required()
def admin_list_feedback():
    schema = AdminListQuerySchema()
    args = schema.load(request.args)
    q = Feedback.query

    if args.get("status"):
        q = q.filter(Feedback.status == args["status"])
    if args.get("type"):
        q = q.filter(Feedback.type == args["type"])

    items, meta = paginate_query(
        q.order_by(Feedback.id.desc()), args["page"], args["per_page"]
    )
    return success_response([fb.to_dict() for fb in items], meta=meta)


@admin_bp.route("/feedback/<int:feedback_id>", methods=["PATCH"])
@admin_required(roles=["super", "editor"])
def admin_update_feedback(feedback_id):
    fb = db.session.get(Feedback, feedback_id)
    if not fb:
        return error_response("NOT_FOUND", "Feedback not found.", status=404)

    schema = AdminFeedbackUpdateSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid status.", errors, 400)

    data = schema.load(request.get_json())
    old_status = fb.status
    fb.status = data["status"]

    log_audit(
        g.current_admin.id,
        "update_feedback",
        "feedback",
        fb.id,
        {"old": old_status, "new": fb.status},
    )
    db.session.commit()
    return success_response(fb.to_dict())


# ── Audit Logs & Analytics ───────────────────────────────────────


@admin_bp.route("/audit-logs", methods=["GET"])
@admin_required()
def admin_list_audit_logs():
    schema = AdminListQuerySchema()
    args = schema.load(request.args)
    q = AuditLog.query

    if args.get("type"):
        q = q.filter(AuditLog.entity_type == args["type"])

    items, meta = paginate_query(
        q.order_by(AuditLog.id.desc()), args["page"], args["per_page"]
    )
    return success_response([log.to_dict() for log in items], meta=meta)


@admin_bp.route("/analytics", methods=["GET"])
@admin_required()
def admin_analytics():
    total_schemes = Scheme.query.count()
    active_schemes = Scheme.query.filter_by(is_active=True).count()
    status_counts = dict(
        db.session.query(Scheme.verification_status, func.count(Scheme.id))
        .group_by(Scheme.verification_status)
        .all()
    )
    level_counts = dict(
        db.session.query(Scheme.level, func.count(Scheme.id))
        .group_by(Scheme.level)
        .all()
    )
    checks_by_status = dict(
        db.session.query(EligibilityCheck.status, func.count(EligibilityCheck.id))
        .group_by(EligibilityCheck.status)
        .all()
    )
    feedback_by_status = dict(
        db.session.query(Feedback.status, func.count(Feedback.id))
        .group_by(Feedback.status)
        .all()
    )

    data = {
        "schemes": {
            "total": total_schemes,
            "active": active_schemes,
            "by_status": status_counts,
            "by_level": level_counts,
        },
        "citizens": {
            "total_users": User.query.count(),
            "total_saved_bookmarks": SavedScheme.query.count(),
        },
        "eligibility": {
            "total_checks": EligibilityCheck.query.count(),
            "by_status": checks_by_status,
        },
        "feedback": {
            "total": Feedback.query.count(),
            "by_status": feedback_by_status,
        },
    }
    return success_response(data)
