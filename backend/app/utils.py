"""SchemeSaathi AI — Response and pagination helpers."""

from flask import jsonify


def success_response(data, meta=None, status=200):
    """Wrap *data* in the standard JSON envelope."""
    return jsonify(data=data, meta=meta, error=None), status


def error_response(code, message, details=None, status=400):
    """Return a standard error envelope."""
    return (
        jsonify(
            data=None,
            meta=None,
            error={"code": code, "message": message, "details": details},
        ),
        status,
    )


def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """Paginate a SQLAlchemy query and return (items, meta)."""
    per_page = min(per_page, max_per_page)
    page = max(page, 1)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    meta = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }
    return pagination.items, meta
