# SchemeSaathi AI

> **The Right Scheme. The Right Guidance. For Every Citizen.**

SchemeSaathi AI is a civic-tech web application that helps Indian citizens
discover government welfare schemes, understand eligibility, and prepare
documents for application.

> ⚠️ **Disclaimer:** This is NOT an official government portal. SchemeSaathi AI
> provides information aggregated from official sources for educational and
> guidance purposes only. Always verify eligibility and application details
> with the respective government department.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS (ES Modules), Lucide Icons |
| Backend | Python 3.11+, Flask, Blueprints, SQLAlchemy, Alembic |
| Database | MySQL 8 |
| AI | Google Gemini API (generation + embeddings), FAISS |
| ML Utilities | scikit-learn, NumPy, Pandas |
| Auth | JWT (httpOnly cookies), Argon2 password hashing |
| Deploy | Render (backend), Netlify/Vercel (frontend) |

## Quick Start

### Option 1: Instant Local Setup (Zero DB Configuration Required)
The repository includes a ready-to-run pre-seeded SQLite database (`schemesaathi_dev.db`) with 12 verified welfare programs and the initial super admin user:

```bash
# Terminal 1 — Backend API
cd backend
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
flask run --port 5000

# Terminal 2 — Frontend Client
cd frontend
python -m http.server 3000
```
Open **`http://localhost:3000`** in any browser.

### Option 2: Full Docker Stack
```bash
docker-compose up --build
```
Spins up MySQL 8, Gunicorn Python API on port 5000, and Nginx Web frontend on port 3000.

---

## Verification & Testing

### 1. Automated Test Suite (301 Tests)
The full test suite covers authentication, RBAC, deterministic rule ASTs, RAG chunking & vector search, multi-factor recommendation scoring, bookmarks, checklist tracking, and admin triage:

```bash
cd backend
pytest tests/ -v
# Output: 301 passed in ~53s (100% passing, 0 regressions)
```

### 2. RAG Evaluation Benchmark (40 Queries in EN, TE, HI)
Evaluates retrieval accuracy and citation correctness against ground truth:

```bash
cd backend
python app/services/rag/evaluator.py
```
- **Hit@1:** 77.5%
- **Hit@3:** 92.5% (Target: ≥ 85%)
- **Hit@5:** 95.0% (Target: ≥ 92%)
- **Telugu Hit@3:** 100.0%
- **Average Query Latency:** 0.44 ms
- Detailed report generated at `docs/eval_report.md`.

## Project Structure

```
schemesaathi/
├── frontend/              # Static HTML/CSS/JS frontend
│   ├── index.html         # Landing page
│   ├── explore.html       # Browse all schemes
│   ├── scheme.html        # Scheme detail page
│   ├── how-it-works.html  # How it works
│   ├── about.html         # About page
│   ├── auth/              # Login, register, forgot password
│   ├── app/               # Authenticated app pages
│   ├── admin/             # Admin panel
│   ├── assets/            # CSS, JS, images, SVGs
│   └── i18n/              # Translations (en, te, hi)
├── backend/               # Flask API server
│   ├── app/               # Application package
│   │   ├── __init__.py    # App factory
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Marshmallow validation
│   │   ├── routes/        # Blueprint route handlers
│   │   └── services/      # Business logic
│   │       ├── eligibility/   # Deterministic rule engine
│   │       ├── recommendation/# Weighted ranking scorer
│   │       └── rag/           # RAG pipeline
│   ├── seeds/             # Seed data (JSON)
│   ├── tests/             # pytest test suite
│   ├── config.py          # Configuration classes
│   ├── extensions.py      # Flask extension instances
│   ├── wsgi.py            # WSGI entry point
│   └── requirements.txt   # Python dependencies
├── data/                  # Document & vector storage
│   ├── raw_docs/          # Original government documents
│   ├── processed/         # Cleaned, chunked documents
│   └── vector_index/      # FAISS index files
├── docs/                  # Documentation
│   ├── architecture.md    # System architecture
│   ├── database-er.md     # Database ER diagram
│   ├── design-tokens.md   # Design token reference
│   ├── api.md             # API documentation
│   ├── sources-to-collect.md # Official sources list
│   └── eval_report.md     # RAG evaluation report
└── README.md              # This file
```

## Principles

1. **Technology should make government support easier to understand,
   not make citizens work harder to access it.**
2. Every scheme record carries `verification_status` — demo data is
   visibly labelled in the UI.
3. Eligibility checks are deterministic (rule engine), not LLM-based.
4. The recommendation engine is weighted ranking, not a "trained model".
5. Chat AI (Saathi) uses RAG with citations — never fabricates information.
6. No PII (name, phone, Aadhaar, bank details) is sent to external APIs.

## Languages Supported

- English (en)
- తెలుగు — Telugu (te)
- हिन्दी — Hindi (hi)

## License

Proprietary — All rights reserved.
