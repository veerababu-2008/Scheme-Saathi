"""SchemeSaathi AI — Scheme validation schemas."""

from marshmallow import Schema, fields, validate


class SchemeQuerySchema(Schema):
    """Query parameters for GET /schemes."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    state = fields.String(load_default=None)
    category = fields.String(load_default=None)
    level = fields.String(
        load_default=None, validate=validate.OneOf(["central", "state"])
    )
    verification_status = fields.String(
        load_default=None,
        validate=validate.OneOf(["verified", "demo", "pending"]),
    )


class SchemeSearchSchema(Schema):
    """Query parameters for GET /schemes/search."""

    q = fields.String(required=True, validate=validate.Length(min=2, max=200))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


class SchemeCreateSchema(Schema):
    """Body for POST /admin/schemes."""

    name = fields.String(required=True, validate=validate.Length(min=3, max=300))
    name_te = fields.String(validate=validate.Length(max=300))
    name_hi = fields.String(validate=validate.Length(max=300))
    slug = fields.String(required=True, validate=validate.Length(min=3, max=300))
    description = fields.String(required=True)
    description_te = fields.String()
    description_hi = fields.String()
    benefits = fields.String(required=True)
    benefits_te = fields.String()
    benefits_hi = fields.String()
    level = fields.String(
        required=True, validate=validate.OneOf(["central", "state"])
    )
    state = fields.String(validate=validate.Length(max=100))
    department = fields.String(validate=validate.Length(max=200))
    ministry = fields.String(validate=validate.Length(max=200))
    apply_url = fields.Url()
    official_url = fields.Url()
    max_benefit_amount = fields.Integer(validate=validate.Range(min=0))
    categories = fields.List(fields.String(), load_default=[])
