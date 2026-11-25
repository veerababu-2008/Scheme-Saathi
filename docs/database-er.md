# SchemeSaathi AI — Database Entity-Relationship Description

> **Engine:** MySQL 8.0 | **ORM:** SQLAlchemy | **Migrations:** Alembic (Flask-Migrate)

---

## ER Diagram (Text)

```
┌──────────────┐       ┌──────────────────┐       ┌───────────────────┐
│   users      │       │  user_profiles   │       │  recently_viewed  │
│──────────────│       │──────────────────│       │───────────────────│
│ id (PK)      │◄──┐   │ id (PK)          │       │ id (PK)           │
│ email        │   │   │ user_id (FK→user)│◄──────│ user_id (FK→user) │
│ password_hash│   │   │ full_name        │       │ scheme_id (FK)    │
│ role         │   │   │ date_of_birth    │       │ viewed_at         │
│ is_active    │   │   │ gender           │       └───────────────────┘
│ created_at   │   │   │ state            │
│ updated_at   │   │   │ district         │       ┌───────────────────┐
└──────────────┘   │   │ pincode          │       │  saved_schemes    │
                   │   │ category (SC/ST…)│       │───────────────────│
                   │   │ religion         │       │ id (PK)           │
                   │   │ occupation       │       │ user_id (FK→user) │
                   │   │ education_level  │       │ scheme_id (FK)    │
                   │   │ annual_income    │       │ saved_at          │
                   │   │ is_bpl           │       │ notes             │
                   │   │ is_minority      │       └───────────────────┘
                   │   │ is_differently_  │
                   │   │   abled          │
                   │   │ marital_status   │
                   │   │ num_dependents   │
                   │   │ land_holding_    │
                   │   │   acres          │
                   │   │ has_bank_account │
                   │   │ profile_complete │
                   │   │   _pct (computed)│
                   │   │ preferred_lang   │
                   │   │ created_at       │
                   │   │ updated_at       │
                   │   └──────────────────┘
                   │
                   │   ┌───────────────────┐     ┌──────────────────────┐
                   │   │  schemes          │     │  scheme_categories   │
                   │   │───────────────────│     │──────────────────────│
                   │   │ id (PK)           │◄───►│ id (PK)              │
                   │   │ name              │     │ scheme_id (FK)       │
                   │   │ name_te           │     │ category (enum)      │
                   │   │ name_hi           │     └──────────────────────┘
                   │   │ slug              │
                   │   │ description       │     ┌──────────────────────┐
                   │   │ description_te    │     │  eligibility_rules   │
                   │   │ description_hi    │     │──────────────────────│
                   │   │ benefits          │     │ id (PK)              │
                   │   │ benefits_te       │     │ scheme_id (FK)       │
                   │   │ benefits_hi       │     │ rules_json (JSON)    │
                   │   │ level (central/   │     │ version (int)        │
                   │   │   state)          │     │ is_active            │
                   │   │ state             │     │ created_at           │
                   │   │ department        │     │ notes                │
                   │   │ ministry          │     └──────────────────────┘
                   │   │ apply_url         │
                   │   │ official_url      │     ┌──────────────────────┐
                   │   │ verification_     │     │  scheme_documents    │
                   │   │   status          │     │──────────────────────│
                   │   │ last_verified_at  │     │ id (PK)              │
                   │   │ is_active (soft   │     │ scheme_id (FK)       │
                   │   │   delete)         │     │ document_name        │
                   │   │ deadline          │     │ document_name_te     │
                   │   │ max_benefit_amt   │     │ document_name_hi     │
                   │   │ created_at        │     │ is_mandatory         │
                   │   │ updated_at        │     │ description          │
                   │   └───────────────────┘     └──────────────────────┘
                   │           │
                   │           │                  ┌──────────────────────┐
                   │           │                  │  scheme_sources      │
                   │           │                  │──────────────────────│
                   │           └─────────────────►│ id (PK)              │
                   │                              │ scheme_id (FK)       │
                   │                              │ source_type          │
                   │                              │   (gazette/url/pdf)  │
                   │                              │ title                │
                   │                              │ url                  │
                   │                              │ retrieved_at         │
                   │                              │ is_primary           │
                   │                              └──────────────────────┘
                   │
                   │   ┌───────────────────┐
                   ├──►│ eligibility_checks │
                   │   │───────────────────│
                   │   │ id (PK)           │
                   │   │ user_id (FK→user) │
                   │   │ scheme_id (FK)    │
                   │   │ status (green/    │
                   │   │   amber/red)      │
                   │   │ result_json       │
                   │   │ checked_at        │
                   │   └───────────────────┘
                   │
                   │   ┌───────────────────┐     ┌──────────────────────┐
                   ├──►│  chat_sessions    │────►│  chat_messages       │
                   │   │───────────────────│     │──────────────────────│
                   │   │ id (PK, UUID)     │     │ id (PK)              │
                   │   │ user_id (FK→user) │     │ session_id (FK)      │
                   │   │ title             │     │ role (user/assistant) │
                   │   │ language          │     │ content              │
                   │   │ created_at        │     │ citations_json       │
                   │   │ updated_at        │     │ created_at           │
                   │   └───────────────────┘     └──────────────────────┘
                   │
                   │   ┌───────────────────┐
                   ├──►│  checklist_       │
                   │   │  progress         │
                   │   │───────────────────│
                   │   │ id (PK)           │
                   │   │ user_id (FK→user) │
                   │   │ scheme_id (FK)    │
                   │   │ document_id (FK)  │
                   │   │ status (pending/  │
                   │   │   collected/na)   │
                   │   │ updated_at        │
                   │   └───────────────────┘
                   │
                   │   ┌───────────────────┐
                   └──►│  feedback         │
                       │───────────────────│
                       │ id (PK)           │
                       │ user_id (FK→user) │
                       │ scheme_id (FK,    │
                       │   nullable)       │
                       │ type (bug/        │
                       │  suggestion/      │
                       │  correction)      │
                       │ message           │
                       │ status (open/     │
                       │   reviewed/done)  │
                       │ created_at        │
                       └───────────────────┘

┌──────────────────┐     ┌──────────────────────┐
│  admin_users     │     │  audit_log           │
│──────────────────│     │──────────────────────│
│ id (PK)          │────►│ id (PK)              │
│ email            │     │ admin_id (FK)        │
│ password_hash    │     │ action               │
│ display_name     │     │ entity_type          │
│ role (super/     │     │ entity_id            │
│   editor/viewer) │     │ diff_json            │
│ is_active        │     │ ip_address           │
│ created_at       │     │ created_at           │
└──────────────────┘     └──────────────────────┘
```

## Table Descriptions

### Core User Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `users` | Authentication records | email (unique), password_hash, role (citizen/admin) | Soft-deletable via is_active |
| `user_profiles` | Citizen profile data for eligibility | All demographic/economic fields | 1:1 with users; profile_complete_pct computed |

### Scheme Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `schemes` | Master scheme records | name, slug (unique), level, state, verification_status | Multilingual (en/te/hi); soft delete via is_active |
| `scheme_categories` | M2M: scheme ↔ category | scheme_id, category (enum) | Categories: agriculture, education, health, housing, employment, social_security, women, minority, disability, startup, pension |
| `eligibility_rules` | Versioned rule JSON per scheme | scheme_id, rules_json, version | Active flag allows rollback; JSON validated on write |
| `scheme_documents` | Required documents for a scheme | scheme_id, document_name, is_mandatory | Multilingual names |
| `scheme_sources` | Provenance / citations | scheme_id, source_type, url | is_primary marks the official gazette/URL |

### User Activity Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `saved_schemes` | Bookmarked schemes | user_id, scheme_id, notes | Unique constraint on (user, scheme) |
| `recently_viewed` | Browsing history | user_id, scheme_id, viewed_at | Capped at 50 per user |
| `eligibility_checks` | Cached check results | user_id, scheme_id, status, result_json | Re-checked when profile changes |
| `checklist_progress` | Per-document readiness | user_id, scheme_id, document_id, status | Status: pending, collected, not_applicable |

### Chat Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `chat_sessions` | Conversation threads | user_id, language, title | UUID primary key |
| `chat_messages` | Individual messages | session_id, role, content, citations_json | citations_json stores source references |

### Admin & Audit Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `admin_users` | Separate admin auth | email, role (super/editor/viewer) | Distinct from citizen users |
| `audit_log` | Admin action trail | admin_id, action, entity_type, diff_json | Immutable; for accountability |
| `feedback` | User-submitted feedback | user_id, type, message, status | Links optionally to a scheme |

## Indexes

| Table | Index | Type | Rationale |
|-------|-------|------|-----------|
| `schemes` | `ix_schemes_state` | B-tree | Filter by state |
| `schemes` | `ix_schemes_is_active` | B-tree | Exclude soft-deleted |
| `schemes` | `ix_schemes_verification_status` | B-tree | Filter by verification |
| `schemes` | `ix_schemes_slug` | Unique | URL lookup |
| `scheme_categories` | `ix_schemecats_category` | B-tree | Category browsing |
| `saved_schemes` | `uq_saved_user_scheme` | Unique | Prevent duplicates |
| `eligibility_checks` | `ix_eligchecks_user` | B-tree | User's check history |
| `chat_sessions` | `ix_chatsessions_user` | B-tree | User's sessions |
| `audit_log` | `ix_audit_created` | B-tree | Chronological queries |

## Cascade Rules

| Parent | Child | On Delete |
|--------|-------|-----------|
| users | user_profiles | CASCADE |
| users | saved_schemes | CASCADE |
| users | recently_viewed | CASCADE |
| users | eligibility_checks | CASCADE |
| users | chat_sessions | CASCADE |
| users | checklist_progress | CASCADE |
| users | feedback | CASCADE |
| schemes | scheme_categories | CASCADE |
| schemes | eligibility_rules | CASCADE |
| schemes | scheme_documents | CASCADE |
| schemes | scheme_sources | CASCADE |
| chat_sessions | chat_messages | CASCADE |
| admin_users | audit_log | RESTRICT (cannot delete admin with logs) |
