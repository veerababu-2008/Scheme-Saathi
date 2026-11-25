"""SchemeSaathi AI — Shared test fixtures."""

import pytest

from app import create_app
from app.models.scheme import EligibilityRule, Scheme, SchemeCategory, SchemeDocument
from extensions import db as _db

# ── App & DB ─────────────────────────────────────────────────────


@pytest.fixture()
def app():
    """Create the application with a fresh in-memory SQLite database."""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client (cookies persist across requests)."""
    return app.test_client()


# ── Auth helpers ─────────────────────────────────────────────────


_TEST_USER = {
    "email": "citizen@example.com",
    "password": "SecurePass1234",
    "full_name": "Test Citizen",
}


@pytest.fixture()
def registered_user(client):
    """Register a citizen user; the *client* retains JWT cookies."""
    resp = client.post("/api/v1/auth/register", json=_TEST_USER)
    assert resp.status_code == 201, resp.get_json()
    return dict(_TEST_USER)


@pytest.fixture()
def auth_client(client, registered_user):
    """A test client already authenticated as a citizen."""
    return client


# ── Seed data ────────────────────────────────────────────────────


_SCHEME_SEEDS = [
    {
        "name": "Test Education Scheme",
        "slug": "test-education",
        "category": "education",
        "level": "central",
        "state": None,
        "max_benefit_amount": 50000,
    },
    {
        "name": "Test Health Scheme",
        "slug": "test-health",
        "category": "health",
        "level": "central",
        "state": None,
        "max_benefit_amount": 500000,
    },
    {
        "name": "Test State Agriculture Scheme",
        "slug": "test-state-agri",
        "category": "agriculture",
        "level": "state",
        "state": "Telangana",
        "max_benefit_amount": 10000,
    },
    {
        "name": "Test Housing Scheme",
        "slug": "test-housing",
        "category": "housing",
        "level": "central",
        "state": None,
        "max_benefit_amount": 120000,
    },
    {
        "name": "Test Women Welfare Scheme",
        "slug": "test-women-welfare",
        "category": "women",
        "level": "state",
        "state": "Telangana",
        "max_benefit_amount": 100000,
    },
]


@pytest.fixture()
def seeded_schemes(app):
    """Insert five test schemes with categories, rules, and documents."""
    with app.app_context():
        for s in _SCHEME_SEEDS:
            scheme = Scheme(
                name=s["name"],
                slug=s["slug"],
                description=f"Description for {s['name']}.",
                benefits=f"Benefits provided by {s['name']}.",
                level=s["level"],
                state=s["state"],
                verification_status="demo",
                is_active=True,
                max_benefit_amount=s["max_benefit_amount"],
            )
            _db.session.add(scheme)
            _db.session.flush()

            _db.session.add(
                SchemeCategory(scheme_id=scheme.id, category=s["category"])
            )
            _db.session.add(
                EligibilityRule(
                    scheme_id=scheme.id,
                    rules_json={
                        "op": "AND",
                        "rules": [
                            {
                                "field": "age",
                                "cmp": "gte",
                                "value": 18,
                                "mandatory": True,
                            }
                        ],
                    },
                    version=1,
                    is_active=True,
                )
            )
            _db.session.add(
                SchemeDocument(
                    scheme_id=scheme.id,
                    document_name="Aadhaar Card",
                    is_mandatory=True,
                    description="Identity proof",
                )
            )

        _db.session.commit()
