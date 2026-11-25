"""SchemeSaathi AI — Profile validation schemas."""

from marshmallow import Schema, fields, validate

_GENDERS = ["male", "female", "other"]
_CATEGORIES = ["General", "SC", "ST", "OBC", "EWS"]
_EDUCATION_LEVELS = [
    "none", "primary", "middle", "secondary", "higher_secondary",
    "diploma", "graduate", "post_graduate", "doctorate",
]
_MARITAL_STATUSES = ["single", "married", "divorced", "widowed"]
_LANGUAGES = ["en", "te", "hi"]


class ProfileUpdateSchema(Schema):
    full_name = fields.String(validate=validate.Length(max=255))
    date_of_birth = fields.Date(format="%Y-%m-%d")
    gender = fields.String(validate=validate.OneOf(_GENDERS))
    state = fields.String(validate=validate.Length(max=100))
    district = fields.String(validate=validate.Length(max=100))
    pincode = fields.String(validate=validate.Regexp(
        r"^\d{6}$", error="Pincode must be exactly 6 digits."
    ))
    category = fields.String(validate=validate.OneOf(_CATEGORIES))
    religion = fields.String(validate=validate.Length(max=50))
    occupation = fields.String(validate=validate.Length(max=100))
    education_level = fields.String(validate=validate.OneOf(_EDUCATION_LEVELS))
    annual_income = fields.Integer(validate=validate.Range(min=0))
    is_bpl = fields.Boolean()
    is_minority = fields.Boolean()
    is_differently_abled = fields.Boolean()
    marital_status = fields.String(validate=validate.OneOf(_MARITAL_STATUSES))
    num_dependents = fields.Integer(validate=validate.Range(min=0, max=20))
    land_holding_acres = fields.Float(validate=validate.Range(min=0))
    has_bank_account = fields.Boolean()
    preferred_language = fields.String(validate=validate.OneOf(_LANGUAGES))
