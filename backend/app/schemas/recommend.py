"""SchemeSaathi AI — Recommendation query validation schemas."""

from marshmallow import Schema, fields, validate


class RecommendQuerySchema(Schema):
    """Query params for GET /recommendations."""

    limit = fields.Integer(
        load_default=10,
        validate=validate.Range(min=1, max=50),
    )
    exclude_red = fields.Boolean(load_default=False)
    category = fields.String(load_default=None)
    state = fields.String(load_default=None)
    level = fields.String(
        load_default=None,
        validate=validate.OneOf(["central", "state"]),
    )
