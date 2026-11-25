"""SchemeSaathi AI — Checklist validation schemas."""

from marshmallow import Schema, fields, validate


class UpdateChecklistSchema(Schema):
    """Body for PUT /checklist/<scheme_id>/documents/<document_id>."""

    status = fields.String(
        required=True,
        validate=validate.OneOf(["pending", "collected", "not_applicable"]),
    )
