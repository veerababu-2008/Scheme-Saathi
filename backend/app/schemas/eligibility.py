"""SchemeSaathi AI — Eligibility route validation schemas."""

from marshmallow import Schema, fields, validate


class CheckAllQuerySchema(Schema):
    """Optional filters for the check-all endpoint."""

    state = fields.String(load_default=None)
    category = fields.String(load_default=None)
    level = fields.String(
        load_default=None,
        validate=validate.OneOf(["central", "state"]),
    )
