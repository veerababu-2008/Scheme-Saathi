"""SchemeSaathi AI — User and authentication models."""

from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from extensions import db

_ph = PasswordHasher()


# ── User ─────────────────────────────────────────────────────────


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20), nullable=False, default="citizen"
    )  # citizen | admin
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    profile = db.relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # ── Password helpers ──

    def set_password(self, password: str):
        self.password_hash = _ph.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            return _ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False

    # ── Serialisation ──

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── User Profile ────────────────────────────────────────────────


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    full_name = db.Column(db.String(255), nullable=False, default="")
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)  # male | female | other
    state = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    category = db.Column(db.String(20), nullable=True)  # General|SC|ST|OBC|EWS
    religion = db.Column(db.String(50), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    education_level = db.Column(db.String(50), nullable=True)
    annual_income = db.Column(db.Integer, nullable=True)
    is_bpl = db.Column(db.Boolean, nullable=True)
    is_minority = db.Column(db.Boolean, nullable=True)
    is_differently_abled = db.Column(db.Boolean, nullable=True)
    marital_status = db.Column(db.String(20), nullable=True)
    num_dependents = db.Column(db.Integer, nullable=True)
    land_holding_acres = db.Column(db.Float, nullable=True)
    has_bank_account = db.Column(db.Boolean, nullable=True)
    preferred_language = db.Column(db.String(5), nullable=False, default="en")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = db.relationship("User", back_populates="profile")

    # ── Computed profile completion ──

    _PROFILE_FIELDS = (
        "full_name", "date_of_birth", "gender", "state", "district",
        "occupation", "education_level", "annual_income", "category",
    )

    @property
    def profile_complete_pct(self) -> int:
        filled = sum(
            1 for f in self._PROFILE_FIELDS if getattr(self, f) not in (None, "")
        )
        return int((filled / len(self._PROFILE_FIELDS)) * 100)

    # ── Age helper ──

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.now(UTC).date()
        dob = self.date_of_birth
        return (
            today.year - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "age": self.age,
            "gender": self.gender,
            "state": self.state,
            "district": self.district,
            "pincode": self.pincode,
            "category": self.category,
            "religion": self.religion,
            "occupation": self.occupation,
            "education_level": self.education_level,
            "annual_income": self.annual_income,
            "is_bpl": self.is_bpl,
            "is_minority": self.is_minority,
            "is_differently_abled": self.is_differently_abled,
            "marital_status": self.marital_status,
            "num_dependents": self.num_dependents,
            "land_holding_acres": self.land_holding_acres,
            "has_bank_account": self.has_bank_account,
            "preferred_language": self.preferred_language,
            "profile_complete_pct": self.profile_complete_pct,
        }


# ── Token Blocklist (for JWT logout) ────────────────────────────


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
