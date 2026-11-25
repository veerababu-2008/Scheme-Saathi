"""SchemeSaathi AI — Auth validation schemas."""

from marshmallow import Schema, fields, validate, validates, ValidationError


def _check_password_strength(value):
    """Shared password-strength validator (used as a field-level validator)."""
    if value.isdigit():
        raise ValidationError("Password cannot be all digits.")
    if len(set(value)) < 4:
        raise ValidationError(
            "Password must contain at least 4 unique characters."
        )


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        validate=[validate.Length(min=8, max=128), _check_password_strength],
    )
    full_name = fields.String(
        load_default="",
        validate=validate.Length(max=255),
    )


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class PasswordChangeSchema(Schema):
    current_password = fields.String(required=True)
    new_password = fields.String(
        required=True,
        validate=[validate.Length(min=8, max=128), _check_password_strength],
    )
