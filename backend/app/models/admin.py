"""SchemeSaathi AI — Admin, audit, and feedback models."""

from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from extensions import db

_ph = PasswordHasher()


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False, default="")
    role = db.Column(
        db.String(20), nullable=False, default="editor"
    )  # super | editor | viewer
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    audit_logs = db.relationship("AuditLog", back_populates="admin")

    def set_password(self, password: str):
        self.password_hash = _ph.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            return _ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "is_active": self.is_active,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(
        db.Integer, db.ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    diff_json = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC),
        index=True,
    )

    admin = db.relationship("AdminUser", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "diff_json": self.diff_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="SET NULL"), nullable=True
    )
    type = db.Column(
        db.String(20), nullable=False
    )  # bug | suggestion | correction
    message = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="open"
    )  # open | reviewed | done
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    user = db.relationship("User", backref="feedback")
    scheme = db.relationship("Scheme", backref="feedback")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "scheme_id": self.scheme_id,
            "type": self.type,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
