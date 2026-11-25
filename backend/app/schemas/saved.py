"""SchemeSaathi AI — Saved-schemes validation schemas."""

from marshmallow import Schema, fields, validate


class SaveSchemeSchema(Schema):
    """Body for POST /saved (bookmark a scheme)."""

    scheme_id = fields.Integer(required=True)
    notes = fields.String(
        load_default=None,
        validate=validate.Length(max=1000),
    )


class UpdateNotesSchema(Schema):
    """Body for PATCH /saved/<id>."""

    notes = fields.String(
        required=True,
        validate=validate.Length(max=1000),
    )


class SavedListSchema(Schema):
    """Query params for GET /saved."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=50),
    )
