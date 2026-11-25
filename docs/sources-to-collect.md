# SchemeSaathi AI — Official Sources to Collect

> **Important:** Only ingest documents from official government sources.
> Every scheme record must carry `verification_status: verified | demo | pending`.
> Demo data must be visibly labelled in the UI.

---

## Priority 1: Central Government Portals

| Source | URL | Content Type | Notes |
|--------|-----|-------------|-------|
| **MyScheme (National)** | https://www.myscheme.gov.in | Scheme listings, eligibility, benefits | Primary aggregator; has API |
| **India.gov.in Services** | https://services.india.gov.in | Service directory | Cross-reference for URLs |
| **PM-KISAN** | https://pmkisan.gov.in | Scheme details, eligibility | Agriculture — high demand |
| **PM Awas Yojana** | https://pmaymis.gov.in | Guidelines, eligibility | Housing — high demand |
| **Ayushman Bharat (PM-JAY)** | https://pmjay.gov.in | Eligibility, benefits, hospitals | Health — flagship scheme |
| **PM Ujjwala Yojana** | https://www.pmujjwalayojana.com | LPG subsidy scheme | Women / BPL focused |
| **National Scholarship Portal** | https://scholarships.gov.in | Scholarship listings | Education — many sub-schemes |
| **e-Shram Portal** | https://eshram.gov.in | Unorganised worker schemes | Employment — large user base |
| **PM SVANidhi** | https://pmsvanidhi.mohua.gov.in | Street vendor loans | Micro-enterprise |
| **NSAP (National Social Asst.)** | https://nsap.nic.in | Pension schemes | Social security |
| **MGNREGA** | https://nrega.nic.in | Rural employment guarantee | Employment — foundational |
| **Gazette of India** | https://egazette.gov.in | Official notifications | For verification of rules |

## Priority 2: State Government (Telangana — Primary State)

| Source | URL | Content Type | Notes |
|--------|-----|-------------|-------|
| **Telangana e-Pass** | https://telanganaepass.cgg.gov.in | Scholarship/fee reimbursement | Education — TS specific |
| **Kalyana Lakshmi / Shaadi Mubarak** | https://telanganaepass.cgg.gov.in | Marriage assistance | Women welfare |
| **Rythu Bandhu** | https://treasury.telangana.gov.in/rythu-bandhu | Farmer investment support | Agriculture — TS flagship |
| **Aasara Pensions** | https://aasara.telangana.gov.in | Social security pensions | Pensions — TS specific |
| **TS Meeseva** | https://ts.meeseva.telangana.gov.in | Government services portal | Multi-service |
| **T-Hub / WE Hub** | https://t-hub.co | Startup / women entrepreneur | Startup ecosystem |

## Priority 3: State Government (Andhra Pradesh)

| Source | URL | Content Type | Notes |
|--------|-----|-------------|-------|
| **AP Navaratnalu** | https://nfrinfra.ap.gov.in | Flagship welfare schemes | Multiple sub-schemes |
| **YSR Pension Kanuka** | — | Social security pensions | High coverage |
| **Jagananna Vidya Deevena** | — | Education fee reimbursement | Education — AP |
| **AP Meeseva** | https://ap.meeseva.gov.in | Government services | Multi-service |

## Priority 4: State Government (Hindi-Speaking States)

| Source | URL | Content Type | Notes |
|--------|-----|-------------|-------|
| **UP Government Schemes** | https://up.gov.in | State scheme portal | Large population |
| **MP Government Schemes** | https://mp.gov.in | State scheme portal | — |
| **Bihar Government Schemes** | https://state.bihar.gov.in | State scheme portal | — |
| **Rajasthan Jan Soochna** | https://jansoochna.rajasthan.gov.in | Transparency portal | Scheme status |

---

## Document Types to Ingest

| Type | Format | Processing |
|------|--------|-----------|
| Scheme guidelines (PDF) | Government PDFs | pdfplumber/PyMuPDF → clean → chunk |
| Official web pages | HTML | trafilatura → clean → chunk |
| Gazette notifications | PDF | pdfplumber → clean → chunk |
| FAQ documents | HTML/PDF | Section-aware chunking |
| Eligibility criteria pages | HTML | Structured extraction |
| Application process guides | HTML/PDF | Step-aware chunking |

## Ingestion Metadata (per chunk)

Every chunk stored in the vector index must carry:
```json
{
  "scheme_id": "pm-kisan",
  "source_url": "https://pmkisan.gov.in/guidelines.pdf",
  "source_title": "PM-KISAN Operational Guidelines 2024",
  "page_number": 12,
  "section_heading": "Eligibility Criteria",
  "language": "en",
  "retrieved_date": "2026-11-24",
  "verification_status": "verified"
}
```

## Collection Process

1. **Manual review**: A human must verify that the source is an official government publication.
2. **Download**: Save raw documents to `data/raw_docs/{scheme_id}/`.
3. **Process**: Run the ingestion pipeline to clean, chunk, and embed.
4. **Verify**: Mark scheme as `verified` only after a human reviews the processed content.
5. **Re-verify**: Set a 90-day re-verification cycle for each source.

> [!IMPORTANT]
> Never scrape or ingest content from unofficial sources, news articles,
> or third-party scheme aggregators without explicit verification.
> The RAG pipeline must only serve information traceable to official documents.

---

## Recommended Collection Order

1. **MyScheme.gov.in** — broadest coverage, most structured data
2. **5 flagship central schemes** (PM-KISAN, PMAY, PM-JAY, NSP, e-Shram)
3. **Telangana state schemes** (primary state for Telugu language support)
4. **AP state schemes** (secondary Telugu-speaking state)
5. **Hindi-belt state schemes** (for Hindi language support)
6. **Remaining central schemes** from MyScheme listings
