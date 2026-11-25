"""SchemeSaathi AI — Chat validation schemas."""

from marshmallow import Schema, fields, validate


class CreateSessionSchema(Schema):
    """Schema for POST /chat/sessions."""

    language = fields.String(
        load_default="en",
        validate=validate.OneOf(["en", "te", "hi"]),
    )
    title = fields.String(
        load_default=None,
        validate=validate.Length(max=200),
    )


class SendMessageSchema(Schema):
    """Schema for POST /chat/sessions/<id>/messages."""

    message = fields.String(
        load_default=None,
        validate=validate.Length(min=1, max=2000),
    )
    content = fields.String(
        load_default=None,
        validate=validate.Length(min=1, max=2000),
    )
    language = fields.String(
        load_default=None,
        validate=validate.OneOf(["en", "te", "hi"]),
    )


class SessionListSchema(Schema):
    """Query params for GET /chat/sessions."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=50),
    )
