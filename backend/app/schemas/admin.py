"""SchemeSaathi AI — Admin validation schemas."""

from marshmallow import Schema, fields, validate


class AdminLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))


class AdminSchemeCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=3, max=300))
    name_te = fields.String(allow_none=True)
    name_hi = fields.String(allow_none=True)
    slug = fields.String(allow_none=True, validate=validate.Length(max=300))
    description = fields.String(required=True, validate=validate.Length(min=10))
    description_te = fields.String(allow_none=True)
    description_hi = fields.String(allow_none=True)
    benefits = fields.String(required=True, validate=validate.Length(min=5))
    benefits_te = fields.String(allow_none=True)
    benefits_hi = fields.String(allow_none=True)
    level = fields.String(validate=validate.OneOf(["central", "state"]))
    state = fields.String(allow_none=True)
    department = fields.String(allow_none=True)
    ministry = fields.String(allow_none=True)
    apply_url = fields.String(allow_none=True)
    official_url = fields.String(allow_none=True)
    verification_status = fields.String(
        validate=validate.OneOf(["pending", "demo", "partially_verified", "verified"])
    )
    is_active = fields.Boolean()
    deadline = fields.Date(allow_none=True)
    max_benefit_amount = fields.Integer(allow_none=True)
    categories = fields.List(fields.String(), allow_none=True)
    documents = fields.List(fields.Dict(), allow_none=True)
    sources = fields.List(fields.Dict(), allow_none=True)


class AdminSchemeUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=3, max=300))
    name_te = fields.String(allow_none=True)
    name_hi = fields.String(allow_none=True)
    slug = fields.String(validate=validate.Length(max=300))
    description = fields.String(validate=validate.Length(min=10))
    description_te = fields.String(allow_none=True)
    description_hi = fields.String(allow_none=True)
    benefits = fields.String(validate=validate.Length(min=5))
    benefits_te = fields.String(allow_none=True)
    benefits_hi = fields.String(allow_none=True)
    level = fields.String(validate=validate.OneOf(["central", "state"]))
    state = fields.String(allow_none=True)
    department = fields.String(allow_none=True)
    ministry = fields.String(allow_none=True)
    apply_url = fields.String(allow_none=True)
    official_url = fields.String(allow_none=True)
    verification_status = fields.String(
        validate=validate.OneOf(["pending", "demo", "partially_verified", "verified"])
    )
    is_active = fields.Boolean()
    deadline = fields.Date(allow_none=True)
    max_benefit_amount = fields.Integer(allow_none=True)
    categories = fields.List(fields.String())


class AdminRuleCreateSchema(Schema):
    rules_json = fields.Dict(required=True)
    notes = fields.String(allow_none=True)


class AdminFeedbackUpdateSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(["open", "reviewed", "done"])
    )


class AdminListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20, validate=validate.Range(min=1, max=100)
    )
    search = fields.String(allow_none=True)
    status = fields.String(allow_none=True)
    type = fields.String(allow_none=True)
    level = fields.String(allow_none=True)
    state = fields.String(allow_none=True)
    category = fields.String(allow_none=True)
