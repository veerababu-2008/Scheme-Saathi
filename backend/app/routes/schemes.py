"""SchemeSaathi AI — Scheme routes (list, search, detail, categories, stats, featured)."""

from flask import Blueprint, request

from app.models.scheme import Scheme, SchemeCategory
from app.schemas.scheme import SchemeQuerySchema, SchemeSearchSchema
from app.utils import error_response, paginate_query, success_response
from extensions import db

schemes_bp = Blueprint("schemes", __name__)


# ── GET / (list with filters) ────────────────────────────────────


@schemes_bp.route("", methods=["GET"], strict_slashes=False)
@schemes_bp.route("/", methods=["GET"], strict_slashes=False)
def list_schemes():
    schema = SchemeQuerySchema()
    errors = schema.validate(request.args)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid parameters.", errors)

    params = schema.load(request.args)
    query = Scheme.query.filter_by(is_active=True)

    if params.get("state"):
        query = query.filter(
            db.or_(Scheme.state == params["state"], Scheme.level == "central")
        )
    if params.get("level"):
        query = query.filter_by(level=params["level"])
    if params.get("verification_status"):
        query = query.filter_by(verification_status=params["verification_status"])
    if params.get("category"):
        query = query.join(SchemeCategory).filter(
            SchemeCategory.category == params["category"]
        )

    query = query.order_by(Scheme.created_at.desc())
    items, meta = paginate_query(query, params["page"], params["per_page"])

    return success_response([s.to_list_dict() for s in items], meta)


# ── GET /search ──────────────────────────────────────────────────


@schemes_bp.route("/search", methods=["GET"])
def search_schemes():
    schema = SchemeSearchSchema()
    errors = schema.validate(request.args)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid parameters.", errors)

    params = schema.load(request.args)
    q = params["q"]

    query = Scheme.query.filter(
        Scheme.is_active == True,
        db.or_(
            Scheme.name.ilike(f"%{q}%"),
            Scheme.name_te.ilike(f"%{q}%"),
            Scheme.name_hi.ilike(f"%{q}%"),
            Scheme.description.ilike(f"%{q}%"),
            Scheme.department.ilike(f"%{q}%"),
            Scheme.benefits.ilike(f"%{q}%"),
        ),
    ).order_by(Scheme.name)

    items, meta = paginate_query(query, params["page"], params["per_page"])
    return success_response([s.to_list_dict() for s in items], meta)


# ── GET /categories ──────────────────────────────────────────────


@schemes_bp.route("/categories", methods=["GET"])
def list_categories():
    rows = (
        db.session.query(
            SchemeCategory.category,
            db.func.count(SchemeCategory.id).label("count"),
        )
        .join(Scheme, SchemeCategory.scheme_id == Scheme.id)
        .filter(Scheme.is_active == True)
        .group_by(SchemeCategory.category)
        .order_by(db.func.count(SchemeCategory.id).desc())
        .all()
    )

    categories = [{"name": row.category, "count": row.count} for row in rows]
    return success_response(categories)


# ── GET /stats ───────────────────────────────────────────────────


@schemes_bp.route("/stats", methods=["GET"])
def scheme_stats():
    total = Scheme.query.filter_by(is_active=True).count()
    verified = Scheme.query.filter_by(is_active=True, verification_status="verified").count()
    central = Scheme.query.filter_by(is_active=True, level="central").count()
    state = Scheme.query.filter_by(is_active=True, level="state").count()

    category_count = (
        db.session.query(SchemeCategory.category)
        .join(Scheme)
        .filter(Scheme.is_active == True)
        .distinct()
        .count()
    )

    return success_response({
        "total_schemes": total,
        "verified_schemes": verified,
        "central_schemes": central,
        "state_schemes": state,
        "categories_covered": category_count,
    })


# ── GET /featured ────────────────────────────────────────────────


@schemes_bp.route("/featured", methods=["GET"])
def featured_schemes():
    schemes = (
        Scheme.query.filter_by(is_active=True)
        .order_by(
            db.case(
                (Scheme.last_verified_at.is_(None), 1),
                else_=0,
            ),
            Scheme.last_verified_at.desc(),
            Scheme.created_at.desc(),
        )
        .limit(6)
        .all()
    )
    return success_response([s.to_list_dict() for s in schemes])


# ── GET /:slug ───────────────────────────────────────────────────


@schemes_bp.route("/<string:slug>", methods=["GET"])
def get_scheme(slug):
    scheme = Scheme.query.filter_by(slug=slug, is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    return success_response(scheme.to_dict(include_rules=True))
