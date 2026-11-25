"""SchemeSaathi AI — User activity models."""

from datetime import UTC, datetime

from extensions import db


class SavedScheme(db.Model):
    __tablename__ = "saved_schemes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    notes = db.Column(db.Text, nullable=True)
    saved_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    user = db.relationship("User", backref="saved_schemes")
    scheme = db.relationship("Scheme", backref="saved_by")

    __table_args__ = (
        db.UniqueConstraint("user_id", "scheme_id", name="uq_saved_user_scheme"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "notes": self.notes,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
        }


class RecentlyViewed(db.Model):
    __tablename__ = "recently_viewed"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    viewed_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    user = db.relationship("User", backref="recently_viewed")
    scheme = db.relationship("Scheme")


class EligibilityCheck(db.Model):
    __tablename__ = "eligibility_checks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    status = db.Column(db.String(10), nullable=False)  # green | amber | red
    result_json = db.Column(db.JSON, nullable=True)
    checked_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    user = db.relationship("User", backref="eligibility_checks")
    scheme = db.relationship("Scheme")

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "status": self.status,
            "result_json": self.result_json,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


class ChecklistProgress(db.Model):
    __tablename__ = "checklist_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey("scheme_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(
        db.String(20), nullable=False, default="pending"
    )  # pending | collected | not_applicable
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = db.relationship("User", backref="checklist_progress")
    scheme = db.relationship("Scheme")
    document = db.relationship("SchemeDocument")

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "document_id": self.document_id,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
