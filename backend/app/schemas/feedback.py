"""SchemeSaathi AI — Feedback validation schemas."""

from marshmallow import Schema, fields, validate


class SubmitFeedbackSchema(Schema):
    """Body for POST /feedback."""

    type = fields.String(
        required=True,
        validate=validate.OneOf(["bug", "suggestion", "correction"]),
    )
    message = fields.String(
        required=True,
        validate=validate.Length(min=10, max=2000),
    )
    scheme_id = fields.Integer(load_default=None)


class FeedbackListSchema(Schema):
    """Query params for GET /feedback."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=50),
    )
    type = fields.String(
        load_default=None,
        validate=validate.OneOf(["bug", "suggestion", "correction"]),
    )
