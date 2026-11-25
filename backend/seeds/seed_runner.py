"""SchemeSaathi AI — Database seed runner (Flask CLI command)."""

import json
import os

import click

from extensions import db
from app.models.scheme import (
    EligibilityRule,
    Scheme,
    SchemeCategory,
    SchemeDocument,
    SchemeSource,
)
from app.models.admin import AdminUser


_SEEDS_DIR = os.path.join(os.path.dirname(__file__))


def register_seed_commands(app):
    """Register 'flask seed' CLI commands on *app*."""

    @app.cli.group()
    def seed():
        """Database seed commands."""

    @seed.command("run")
    @click.option("--force", is_flag=True, help="Drop and re-seed scheme data.")
    def seed_run(force):
        """Seed the database with demo schemes and admin user."""
        _seed_schemes(force)
        _seed_admin()
        click.echo("✓ Seed complete.")

    @seed.command("schemes")
    @click.option("--force", is_flag=True)
    def seed_schemes_cmd(force):
        """Seed only scheme data."""
        _seed_schemes(force)

    @seed.command("admin")
    def seed_admin_cmd():
        """Seed only admin user."""
        _seed_admin()


def _seed_schemes(force=False):
    """Load schemes from seeds/schemes.json into the database."""
    if force:
        click.echo("  Clearing existing scheme data …")
        SchemeSource.query.delete()
        SchemeDocument.query.delete()
        EligibilityRule.query.delete()
        SchemeCategory.query.delete()
        Scheme.query.delete()
        db.session.commit()

    existing_slugs = {s.slug for s in Scheme.query.with_entities(Scheme.slug).all()}

    path = os.path.join(_SEEDS_DIR, "schemes.json")
    with open(path, "r", encoding="utf-8") as f:
        schemes_data = json.load(f)

    added = 0
    for entry in schemes_data:
        if entry["slug"] in existing_slugs:
            click.echo(f"  Skip (exists): {entry['slug']}")
            continue

        scheme = Scheme(
            name=entry["name"],
            name_te=entry.get("name_te"),
            name_hi=entry.get("name_hi"),
            slug=entry["slug"],
            description=entry.get("description", ""),
            description_te=entry.get("description_te"),
            description_hi=entry.get("description_hi"),
            benefits=entry.get("benefits", ""),
            benefits_te=entry.get("benefits_te"),
            benefits_hi=entry.get("benefits_hi"),
            level=entry.get("level", "central"),
            state=entry.get("state"),
            department=entry.get("department"),
            ministry=entry.get("ministry"),
            apply_url=entry.get("apply_url"),
            official_url=entry.get("official_url"),
            verification_status=entry.get("verification_status", "demo"),
            max_benefit_amount=entry.get("max_benefit_amount"),
            is_active=True,
        )
        db.session.add(scheme)
        db.session.flush()  # get scheme.id

        # Categories
        for cat_name in entry.get("categories", []):
            db.session.add(
                SchemeCategory(scheme_id=scheme.id, category=cat_name)
            )

        # Documents
        for doc in entry.get("documents", []):
            db.session.add(
                SchemeDocument(
                    scheme_id=scheme.id,
                    document_name=doc["document_name"],
                    document_name_te=doc.get("document_name_te"),
                    document_name_hi=doc.get("document_name_hi"),
                    is_mandatory=doc.get("is_mandatory", True),
                    description=doc.get("description"),
                )
            )

        # Sources
        for src in entry.get("sources", []):
            db.session.add(
                SchemeSource(
                    scheme_id=scheme.id,
                    source_type=src.get("source_type", "url"),
                    title=src["title"],
                    url=src.get("url"),
                    is_primary=src.get("is_primary", False),
                )
            )

        # Eligibility rules
        rules = entry.get("eligibility_rules")
        if rules:
            db.session.add(
                EligibilityRule(
                    scheme_id=scheme.id,
                    rules_json=rules,
                    version=1,
                    is_active=True,
                    notes="Initial seed – demo data",
                )
            )

        added += 1

    db.session.commit()
    click.echo(f"  ✓ Schemes seeded: {added} added, {len(existing_slugs)} existed.")


def _seed_admin():
    """Create the initial admin user if it does not exist."""
    email = os.getenv("ADMIN_INITIAL_EMAIL", "admin@schemesaathi.in")
    password = os.getenv("ADMIN_INITIAL_PASSWORD", "change-me-on-first-login")

    if AdminUser.query.filter_by(email=email).first():
        click.echo(f"  Skip admin (exists): {email}")
        return

    admin = AdminUser(email=email, display_name="Admin", role="super")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"  ✓ Admin user created: {email}")
