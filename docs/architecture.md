# SchemeSaathi AI — Architecture Document

> **Version:** 0.1.0 (Phase 0)
> **Last updated:** 2026-11-24

---

## 1. System Overview

SchemeSaathi AI is a civic-tech web application that helps Indian citizens
discover government welfare schemes, understand eligibility, and prepare
documents for application. It is **not** an official government portal.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT  (Browser)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Landing /   │  │  Citizen    │  │  Saathi AI   │  │  Admin    │ │
│  │  Public Pages│  │  Dashboard  │  │  Chat Panel  │  │  Panel    │ │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                │                │       │
│         └────────────┬────┴────────┬───────┘                │       │
│                      │  api.js     │                        │       │
│                      │  (fetch)    │                        │       │
└──────────────────────┼─────────────┼────────────────────────┼───────┘
                       │  HTTPS/JSON │                        │
┌──────────────────────┼─────────────┼────────────────────────┼───────┐
│                      ▼             ▼                        ▼       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Flask Application                           ││
│  │  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐ ││
│  │  │  Auth    │  │  Schemes  │  │  Eligibi-  │  │  Chat /      │ ││
│  │  │  Routes  │  │  Routes   │  │  lity API  │  │  RAG Routes  │ ││
│  │  │  (BP)    │  │  (BP)     │  │  (BP)      │  │  (BP)        │ ││
│  │  └────┬─────┘  └────┬──────┘  └─────┬──────┘  └──────┬───────┘ ││
│  │       │              │               │                │        ││
│  │  ┌────▼──────────────▼───────────────▼────────────────▼───────┐ ││
│  │  │                    SERVICE LAYER                           │ ││
│  │  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐ │ ││
│  │  │  │Eligibili-│  │Recommendation│  │  RAG Pipeline        │ │ ││
│  │  │  │ty Engine │  │  Scorer      │  │  ┌────────────────┐  │ │ ││
│  │  │  │(determin-│  │  (weighted   │  │  │ingest → clean  │  │ │ ││
│  │  │  │istic,    │  │   ranking,   │  │  │→ chunk → embed │  │ │ ││
│  │  │  │ no LLM)  │  │   no ML)     │  │  │→ FAISS index   │  │ │ ││
│  │  │  └──────────┘  └──────────────┘  │  │→ retrieve      │  │ │ ││
│  │  │                                  │  │→ Gemini answer  │  │ │ ││
│  │  │                                  │  └────────────────┘  │ │ ││
│  │  │                                  └──────────────────────┘ │ ││
│  │  └──────────────────────────────────────────────────────────-┘ ││
│  │                           │                                    ││
│  │       ┌───────────────────┼──────────────────┐                 ││
│  │       ▼                   ▼                  ▼                 ││
│  │  ┌─────────┐     ┌──────────────┐    ┌──────────────┐          ││
│  │  │ MySQL 8 │     │ FAISS Index  │    │ Gemini API   │          ││
│  │  │ (users, │     │ (vector_index│    │ (generation  │          ││
│  │  │ schemes,│     │  /faiss.idx) │    │  + embeddings│          ││
│  │  │ rules…) │     └──────────────┘    └──────────────┘          ││
│  │  └─────────┘                                                   ││
│  └────────────────────────────────────────────────────────────────┘│
│                       SERVER  (Render / gunicorn)                   │
└────────────────────────────────────────────────────────────────────┘
```

## 2. Architectural Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Vanilla JS frontend, no framework | Keeps bundle size near zero, reduces dependency risk, matches civic-tech audience (slow connections). |
| 2 | Flask Blueprints (one per domain) | Clean separation; each blueprint is independently testable. |
| 3 | Deterministic eligibility engine | Auditability — citizens can see exactly which rules passed or failed. No LLM black box for eligibility. |
| 4 | RAG for Saathi AI chat, not fine-tuning | Avoids training cost, allows real-time source updates, provides citations. |
| 5 | FAISS over ChromaDB (default) | Simpler deployment (single file), sufficient at <100k vectors. ChromaDB available as a swap. |
| 6 | MySQL 8 | Mature RDBMS, strong JSON support for eligibility rules, widely available managed hosting. |
| 7 | JWT in httpOnly cookies | Prevents XSS token theft while keeping the API stateless. |
| 8 | Gemini API (not OpenAI) | Multilingual (EN/TE/HI) capability, embedding + generation in one provider. |

## 3. Data Flow Diagrams

### 3.1 Eligibility Check Flow

```
User submits profile
        │
        ▼
  Load scheme's eligibility_rules (JSON)
        │
        ▼
  For each leaf rule:
    ├── Profile has the field? ──No──▶ result = UNKNOWN
    │        │
    │       Yes
    │        │
    │        ▼
    │   Evaluate comparator (eq/neq/gt/gte/lt/lte/in/between)
    │        │
    │   ┌────┴────┐
    │   TRUE    FALSE
    │
    ▼
  Combine via AND/OR tree logic
        │
  ┌─────┼──────────┐
  │     │          │
GREEN  AMBER     RED
(all   (some     (any mandatory
 met)  unknown)  failed)
        │
        ▼
  Return: status, met[], not_met[], missing[], explanation, sources
```

### 3.2 RAG Chat Flow

```
User question (+ language hint)
        │
        ▼
  Detect language (or use override)
        │
        ▼
  Embed question via Gemini Embedding API
        │
        ▼
  FAISS similarity search (top-k=6, filtered by scheme/state/language)
        │
        ▼
  Build prompt: system rules + retrieved chunks + question
        │
        ▼
  Gemini Generation API → candidate answer
        │
        ▼
  Validator: citations present? numbers match chunks?
    ├── PASS → return answer + source cards
    └── FAIL → regenerate (max 2 retries) or return "I could not find…"
```

### 3.3 Recommendation Scoring

```
For each active scheme (excluding RED-status schemes):
  score = 0.30 × semantic_similarity(user_query, scheme_embedding)
        + 0.30 × profile_match_ratio(user_profile, scheme_rules)
        + 0.15 × category_affinity(user_interests, scheme_category)
        + 0.15 × location_match(user_state, scheme_states)
        + 0.10 × freshness_score(scheme.last_verified_at)

Sort descending → attach "Why this?" reasons → return top N
```

## 4. Request Lifecycle

```
Browser                 Flask                            MySQL / FAISS / Gemini
   │                       │                                      │
   │── POST /api/v1/xxx ──▶│                                      │
   │   (httpOnly cookie)   │── validate JWT ──┐                   │
   │                       │                  │                   │
   │                       │◀── user context ─┘                   │
   │                       │                                      │
   │                       │── marshmallow validate body ──┐      │
   │                       │                               │      │
   │                       │◀── clean data ────────────────┘      │
   │                       │                                      │
   │                       │── service layer ──────────────────▶ │
   │                       │                                      │
   │                       │◀── result / error ◀──────────────── │
   │                       │                                      │
   │◀── JSON response ────│                                      │
   │   {data, meta, error} │                                      │
```

## 5. Deployment Topology

```
┌──────────────┐       ┌────────────────────┐       ┌───────────────┐
│  Netlify /   │       │   Render           │       │  Aiven /      │
│  Vercel      │──────▶│   (gunicorn +      │──────▶│  Railway      │
│  (static     │ HTTPS │    Flask app)      │  TCP  │  (MySQL 8     │
│   frontend)  │       │                    │       │   managed)    │
└──────────────┘       │   + FAISS index    │       └───────────────┘
                       │     in /data/      │
                       │                    │       ┌───────────────┐
                       │                    │──────▶│  Google       │
                       │                    │ HTTPS │  Gemini API   │
                       └────────────────────┘       └───────────────┘
```

## 6. Security Architecture

| Layer | Mechanism |
|-------|-----------|
| Auth | Argon2id password hashing, JWT (httpOnly, Secure, SameSite=Lax) |
| CSRF | Double-submit cookie pattern |
| Input | marshmallow/pydantic validation on every endpoint |
| SQL | SQLAlchemy ORM (parameterised), no raw SQL |
| XSS | Context-aware output escaping in templates, CSP headers |
| Upload | Allowlist MIME types, max 10 MB, virus-scan hook (future) |
| Rate limit | Flask-Limiter: 5/min on auth, 20/min on chat, 60/min general |
| Headers | HSTS, X-Content-Type-Options, X-Frame-Options, CSP |
| Privacy | No PII sent to Gemini (only age band, state, occupation) |
| Audit | Admin actions logged with user_id, action, timestamp, diff |
| Data rights | Export (JSON) and hard-delete account endpoints |

## 7. Module Boundaries

| Module | Responsibility | Dependencies |
|--------|----------------|-------------|
| `routes/auth.py` | Register, login, logout, refresh, password change | `services/auth_service`, `models/user` |
| `routes/schemes.py` | List, search, detail, CRUD (admin) | `models/scheme`, `schemas/scheme` |
| `routes/eligibility.py` | Check one scheme, check all | `services/eligibility/engine` |
| `routes/chat.py` | Send message, list sessions, history | `services/rag/*`, `services/gemini_client` |
| `routes/recommend.py` | Get recommendations | `services/recommendation/scorer` |
| `services/eligibility/engine.py` | Recursive rule evaluator | `operators.py`, `explain.py` |
| `services/rag/retriever.py` | Embed query, search FAISS, filter | `embeddings.py`, `vector_store.py` |
| `services/rag/prompt.py` | Build system + context prompt | — |
| `services/rag/validator.py` | Check citations, numbers | — |
| `services/gemini_client.py` | Thin wrapper for Gemini API calls | `google-generativeai` SDK |
