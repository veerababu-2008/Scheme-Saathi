"""SchemeSaathi AI — Document checklist routes.

Tracks which required documents a user has collected for a scheme.

Endpoints:
  GET  /checklist/<scheme_id>                           List documents with status
  PUT  /checklist/<scheme_id>/documents/<document_id>   Update document status
  GET  /checklist/summary                               Cross-scheme summary
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from app.models.scheme import Scheme, SchemeDocument
from app.models.activity import ChecklistProgress
from app.schemas.checklist import UpdateChecklistSchema
from app.utils import error_response, success_response

checklist_bp = Blueprint("checklist", __name__)


# ── GET /checklist/<scheme_id> ───────────────────────────────────


@checklist_bp.route("/<int:scheme_id>", methods=["GET"])
@jwt_required()
def get_checklist(scheme_id):
    """List all required documents for a scheme with the user's progress."""
    user_id = int(get_jwt_identity())

    scheme = Scheme.query.filter_by(id=scheme_id, is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    documents = SchemeDocument.query.filter_by(scheme_id=scheme_id).all()

    # Fetch existing progress
    progress_map = {}
    progresses = ChecklistProgress.query.filter_by(
        user_id=user_id, scheme_id=scheme_id
    ).all()
    for p in progresses:
        progress_map[p.document_id] = p

    items = []
    collected = 0
    total = len(documents)

    for doc in documents:
        progress = progress_map.get(doc.id)
        status = progress.status if progress else "pending"
        if status == "collected":
            collected += 1

        items.append({
            "document_id": doc.id,
            "document_name": doc.document_name,
            "document_name_te": doc.document_name_te,
            "document_name_hi": doc.document_name_hi,
            "is_mandatory": doc.is_mandatory,
            "description": doc.description,
            "status": status,
        })

    return success_response({
        "scheme_id": scheme.id,
        "scheme_name": scheme.name,
        "total_documents": total,
        "collected_count": collected,
        "completion_pct": int((collected / total * 100)) if total else 100,
        "documents": items,
    })


# ── PUT /checklist/<scheme_id>/documents/<document_id> ───────────


@checklist_bp.route(
    "/<int:scheme_id>/documents/<int:document_id>", methods=["PUT"]
)
@jwt_required()
def update_document_status(scheme_id, document_id):
    """Update the status of a document in the user's checklist."""
    user_id = int(get_jwt_identity())

    scheme = Scheme.query.filter_by(id=scheme_id, is_active=True).first()
    if not scheme:
        return error_response("NOT_FOUND", "Scheme not found.", status=404)

    document = SchemeDocument.query.filter_by(
        id=document_id, scheme_id=scheme_id
    ).first()
    if not document:
        return error_response("NOT_FOUND", "Document not found.", status=404)

    schema = UpdateChecklistSchema()
    errors = schema.validate(request.get_json(silent=True) or {})
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid input.", errors, 400)

    data = schema.load(request.get_json())

    progress = ChecklistProgress.query.filter_by(
        user_id=user_id, scheme_id=scheme_id, document_id=document_id
    ).first()

    if progress:
        progress.status = data["status"]
    else:
        progress = ChecklistProgress(
            user_id=user_id,
            scheme_id=scheme_id,
            document_id=document_id,
            status=data["status"],
        )
        db.session.add(progress)

    db.session.commit()

    return success_response({
        "document_id": document_id,
        "document_name": document.document_name,
        "status": progress.status,
    })


# ── GET /checklist/summary ───────────────────────────────────────


@checklist_bp.route("/summary", methods=["GET"])
@jwt_required()
def checklist_summary():
    """Return a cross-scheme document preparation summary."""
    user_id = int(get_jwt_identity())

    progresses = ChecklistProgress.query.filter_by(user_id=user_id).all()

    scheme_ids = set(p.scheme_id for p in progresses)
    schemes_summary = []

    for sid in scheme_ids:
        scheme = db.session.get(Scheme, sid)
        if not scheme or not scheme.is_active:
            continue

        total_docs = SchemeDocument.query.filter_by(scheme_id=sid).count()
        collected = sum(
            1 for p in progresses
            if p.scheme_id == sid and p.status == "collected"
        )

        schemes_summary.append({
            "scheme_id": sid,
            "scheme_name": scheme.name,
            "scheme_slug": scheme.slug,
            "total_documents": total_docs,
            "collected_count": collected,
            "completion_pct": int((collected / total_docs * 100)) if total_docs else 100,
        })

    schemes_summary.sort(key=lambda s: s["completion_pct"], reverse=True)

    return success_response({
        "total_schemes": len(schemes_summary),
        "schemes": schemes_summary,
    })
