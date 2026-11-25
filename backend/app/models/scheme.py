"""SchemeSaathi AI — Scheme-related models."""

from datetime import datetime, timezone

from extensions import db


# ── Scheme (master record) ───────────────────────────────────────


class Scheme(db.Model):
    __tablename__ = "schemes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    name_te = db.Column(db.String(300), nullable=True)
    name_hi = db.Column(db.String(300), nullable=True)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    description_te = db.Column(db.Text, nullable=True)
    description_hi = db.Column(db.Text, nullable=True)
    benefits = db.Column(db.Text, nullable=False, default="")
    benefits_te = db.Column(db.Text, nullable=True)
    benefits_hi = db.Column(db.Text, nullable=True)
    level = db.Column(db.String(20), nullable=False, default="central")  # central|state
    state = db.Column(db.String(100), nullable=True, index=True)
    department = db.Column(db.String(200), nullable=True)
    ministry = db.Column(db.String(200), nullable=True)
    apply_url = db.Column(db.String(500), nullable=True)
    official_url = db.Column(db.String(500), nullable=True)
    verification_status = db.Column(
        db.String(20), nullable=False, default="pending", index=True
    )  # verified | demo | pending
    last_verified_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    deadline = db.Column(db.Date, nullable=True)
    max_benefit_amount = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    categories = db.relationship(
        "SchemeCategory", back_populates="scheme", cascade="all, delete-orphan"
    )
    eligibility_rules = db.relationship(
        "EligibilityRule", back_populates="scheme", cascade="all, delete-orphan"
    )
    documents = db.relationship(
        "SchemeDocument", back_populates="scheme", cascade="all, delete-orphan"
    )
    sources = db.relationship(
        "SchemeSource", back_populates="scheme", cascade="all, delete-orphan"
    )

    @property
    def active_rules(self):
        """Return the latest active eligibility rule set."""
        return (
            EligibilityRule.query
            .filter_by(scheme_id=self.id, is_active=True)
            .order_by(EligibilityRule.version.desc())
            .first()
        )

    def to_dict(self, include_rules=False):
        data = {
            "id": self.id,
            "name": self.name,
            "name_te": self.name_te,
            "name_hi": self.name_hi,
            "slug": self.slug,
            "description": self.description,
            "description_te": self.description_te,
            "description_hi": self.description_hi,
            "benefits": self.benefits,
            "benefits_te": self.benefits_te,
            "benefits_hi": self.benefits_hi,
            "level": self.level,
            "state": self.state,
            "department": self.department,
            "ministry": self.ministry,
            "apply_url": self.apply_url,
            "official_url": self.official_url,
            "verification_status": self.verification_status,
            "last_verified_at": (
                self.last_verified_at.isoformat()
                if self.last_verified_at
                else None
            ),
            "is_active": self.is_active,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "max_benefit_amount": self.max_benefit_amount,
            "categories": [c.category for c in self.categories],
            "documents": [d.to_dict() for d in self.documents],
            "sources": [s.to_dict() for s in self.sources],
        }
        if include_rules and self.active_rules:
            data["eligibility_rules"] = self.active_rules.to_dict()
        return data

    def to_list_dict(self):
        """Lightweight dict for list/search endpoints."""
        return {
            "id": self.id,
            "name": self.name,
            "name_te": self.name_te,
            "name_hi": self.name_hi,
            "slug": self.slug,
            "description": self.description[:200],
            "benefits": self.benefits[:200],
            "level": self.level,
            "state": self.state,
            "department": self.department,
            "verification_status": self.verification_status,
            "max_benefit_amount": self.max_benefit_amount,
            "categories": [c.category for c in self.categories],
        }


# ── Scheme ↔ Category (M2M) ─────────────────────────────────────


class SchemeCategory(db.Model):
    __tablename__ = "scheme_categories"

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    category = db.Column(db.String(50), nullable=False, index=True)

    scheme = db.relationship("Scheme", back_populates="categories")

    __table_args__ = (
        db.UniqueConstraint("scheme_id", "category", name="uq_scheme_category"),
    )


# ── Eligibility Rules (versioned JSON) ──────────────────────────


class EligibilityRule(db.Model):
    __tablename__ = "eligibility_rules"

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    rules_json = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    scheme = db.relationship("Scheme", back_populates="eligibility_rules")

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "rules_json": self.rules_json,
            "version": self.version,
            "is_active": self.is_active,
            "notes": self.notes,
        }


# ── Scheme Documents (required paperwork) ───────────────────────


class SchemeDocument(db.Model):
    __tablename__ = "scheme_documents"

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_name = db.Column(db.String(200), nullable=False)
    document_name_te = db.Column(db.String(200), nullable=True)
    document_name_hi = db.Column(db.String(200), nullable=True)
    is_mandatory = db.Column(db.Boolean, nullable=False, default=True)
    description = db.Column(db.Text, nullable=True)

    scheme = db.relationship("Scheme", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "document_name": self.document_name,
            "document_name_te": self.document_name_te,
            "document_name_hi": self.document_name_hi,
            "is_mandatory": self.is_mandatory,
            "description": self.description,
        }


# ── Scheme Sources (provenance / citations) ─────────────────────


class SchemeSource(db.Model):
    __tablename__ = "scheme_sources"

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(
        db.Integer, db.ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = db.Column(
        db.String(20), nullable=False, default="url"
    )  # gazette | url | pdf
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    retrieved_at = db.Column(db.DateTime, nullable=True)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)

    scheme = db.relationship("Scheme", back_populates="sources")

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "is_primary": self.is_primary,
        }
