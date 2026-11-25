# SchemeSaathi AI — API Specification (v1)

> **Base URL:** `/api/v1`
> **Format:** JSON (all requests and responses)
> **Auth:** JWT in httpOnly cookies

---

## Standard Response Shape

```json
{
  "data": { ... },
  "meta": { "page": 1, "per_page": 20, "total": 142 },
  "error": null
}
```

```json
{
  "data": null,
  "meta": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Annual income must be a positive number.",
    "details": { "field": "annual_income", "constraint": "gt:0" }
  }
}
```

---

## Endpoints

### Auth (`/api/v1/auth`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| POST | `/register` | Create citizen account | 5/min | No |
| POST | `/login` | Login, set JWT cookie | 5/min | No |
| POST | `/logout` | Clear JWT cookie | 60/min | Yes |
| POST | `/refresh` | Refresh access token | 10/min | Yes (refresh) |
| PUT | `/password` | Change password | 5/min | Yes |

### Profile (`/api/v1/profile`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| GET | `/` | Get current user profile | 60/min | Yes |
| PUT | `/` | Update profile fields | 60/min | Yes |
| GET | `/completion` | Profile completion percentage | 60/min | Yes |
| POST | `/export` | Export all user data (JSON) | 2/hour | Yes |
| DELETE | `/account` | Hard-delete account & all data | 2/hour | Yes |

### Schemes (`/api/v1/schemes`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| GET | `/` | List schemes (paginated, filterable) | 60/min | No |
| GET | `/search?q=...` | Full-text search | 60/min | No |
| GET | `/:slug` | Scheme detail | 60/min | No |
| GET | `/categories` | List all categories with counts | 60/min | No |
| GET | `/stats` | Aggregate stats for landing page | 60/min | No |
| GET | `/featured` | Featured schemes for landing | 60/min | No |

### Eligibility (`/api/v1/eligibility`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| POST | `/check/:scheme_id` | Check one scheme | 30/min | Yes |
| POST | `/check-all` | Check all active schemes | 10/min | Yes |
| GET | `/history` | Past eligibility checks | 60/min | Yes |

### Recommendations (`/api/v1/recommendations`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| GET | `/` | Personalised recommendations | 20/min | Yes |

### Chat / Saathi AI (`/api/v1/chat`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| POST | `/sessions` | Create new chat session | 20/min | Yes |
| GET | `/sessions` | List user's sessions | 60/min | Yes |
| GET | `/sessions/:id` | Get session messages | 60/min | Yes |
| POST | `/sessions/:id/messages` | Send message, get AI reply | 20/min | Yes |
| DELETE | `/sessions/:id` | Delete a session | 60/min | Yes |

### Saved Schemes (`/api/v1/saved`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| GET | `/` | List saved schemes | 60/min | Yes |
| POST | `/` | Save/bookmark a scheme | 60/min | Yes |
| DELETE | `/:scheme_id` | Remove bookmark | 60/min | Yes |
| PUT | `/:scheme_id/notes` | Update notes | 60/min | Yes |

### Checklist (`/api/v1/checklist`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| GET | `/:scheme_id` | Get checklist for a scheme | 60/min | Yes |
| PUT | `/:scheme_id/:doc_id` | Update document status | 60/min | Yes |

### Feedback (`/api/v1/feedback`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| POST | `/` | Submit feedback | 10/min | Yes |
| GET | `/mine` | List user's feedback | 60/min | Yes |

### Admin (`/api/v1/admin`)

| Method | Path | Description | Rate Limit | Auth |
|--------|------|-------------|-----------|------|
| POST | `/login` | Admin login | 5/min | No |
| GET | `/schemes` | List all schemes (inc. inactive) | 60/min | Admin |
| POST | `/schemes` | Create scheme | 60/min | Admin |
| PUT | `/schemes/:id` | Update scheme | 60/min | Admin |
| DELETE | `/schemes/:id` | Soft-delete scheme | 60/min | Admin |
| PUT | `/schemes/:id/verify` | Set verification status | 60/min | Admin |
| POST | `/schemes/:id/sources` | Add source | 60/min | Admin |
| PUT | `/schemes/:id/rules` | Update eligibility rules | 60/min | Admin |
| GET | `/feedback` | List all feedback | 60/min | Admin |
| PUT | `/feedback/:id` | Update feedback status | 60/min | Admin |
| GET | `/analytics` | Dashboard analytics | 60/min | Admin |
| GET | `/audit-log` | View audit trail | 60/min | Admin (super) |

---

## Pagination

Query parameters: `page` (default 1), `per_page` (default 20, max 100).

## Filtering (Schemes)

Query parameters: `state`, `category`, `level` (central/state),
`verification_status`, `is_active`.

## Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `VALIDATION_ERROR` | 400 | Request body/params invalid |
| `UNAUTHORIZED` | 401 | Missing or expired JWT |
| `FORBIDDEN` | 403 | Insufficient role |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Duplicate (e.g., email exists) |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
