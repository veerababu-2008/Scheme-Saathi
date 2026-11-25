# SchemeSaathi AI — Design Token Reference & Contrast Table

> **Source of truth:** `frontend/assets/css/tokens.css`
> All text/background pairs must meet WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text).

---

## Colour Palette Overview

### Distribution Target
| Role | % of Surface | Tokens |
|------|-------------|--------|
| Parchment / Warm White | 55% | `--parchment-50`, `--parchment-100`, `--warm-white` |
| Aubergine | 20% | `--aubergine-900`, `--aubergine-800`, `--aubergine-600` |
| Neutral surfaces | 12% | `--rose-clay`, `--mist-sage`, `--line` |
| Vermilion | 8% | `--vermilion-500`, `--vermilion-600`, `--vermilion-700` |
| Jade / Brass / Status | 5% | `--jade-*`, `--amber-*`, `--oxblood-*`, `--brass-*` |

### Usage Rules
- **Vermilion**: Primary actions and ONE highlight per screen only.
- **Jade**: Positive/verified status only. Never decorative.
- **Oxblood** (not vermilion): Negative status only.
- **Brass**: Premium accents; `--brass-700` for any text on light backgrounds. `--brass-500` never for small text.
- **Status colours**: Never mix roles (jade for positive, amber for warning, oxblood for negative).

---

## WCAG AA Contrast Table (Light Mode)

| Foreground | Background | Use Case | Ratio | Pass? |
|-----------|-----------|----------|-------|-------|
| `--ink` (#272522) | `--parchment-100` (#F6F0E5) | Body text | 12.1:1 | ✅ AAA |
| `--ink` (#272522) | `--warm-white` (#FFFCF6) | Card body text | 13.5:1 | ✅ AAA |
| `--ink-muted` (#5E5750) | `--parchment-100` (#F6F0E5) | Secondary text | 5.6:1 | ✅ AA |
| `--ink-muted` (#5E5750) | `--warm-white` (#FFFCF6) | Muted card text | 6.2:1 | ✅ AA |
| `--aubergine-800` (#302033) | `--parchment-100` (#F6F0E5) | Headings | 10.7:1 | ✅ AAA |
| `--aubergine-800` (#302033) | `--warm-white` (#FFFCF6) | Card headings | 11.9:1 | ✅ AAA |
| `#FFFFFF` | `--aubergine-800` (#302033) | Nav text on dark | 11.9:1 | ✅ AAA |
| `#FFFFFF` | `--aubergine-900` (#231826) | Footer text | 14.4:1 | ✅ AAA |
| `#FFFFFF` | `--vermilion-600` (#B3412A) | Button label | 4.6:1 | ✅ AA |
| `#FFFFFF` | `--vermilion-700` (#963520) | Button hover | 5.9:1 | ✅ AA |
| `--vermilion-500` (#C64E35) | `--parchment-100` (#F6F0E5) | Accent text (large) | 3.6:1 | ✅ AA-large |
| `--jade-600` (#527966) | `--jade-100` (#DDEBE3) | Positive status text | 4.0:1 | ✅ AA-large |
| `--jade-600` (#527966) | `--warm-white` (#FFFCF6) | Positive chip text | 5.0:1 | ✅ AA |
| `--amber-700` (#8A5A0B) | `--amber-100` (#F6E7C4) | Warning status text | 4.5:1 | ✅ AA |
| `--oxblood-700` (#8E2F3A) | `--oxblood-100` (#F2D9D8) | Negative status text | 4.7:1 | ✅ AA |
| `--brass-700` (#7D5C26) | `--parchment-100` (#F6F0E5) | Premium text | 5.0:1 | ✅ AA |
| `--brass-700` (#7D5C26) | `--warm-white` (#FFFCF6) | Premium card text | 5.6:1 | ✅ AA |

## WCAG AA Contrast Table (Dark Mode)

| Foreground | Background | Use Case | Ratio | Pass? |
|-----------|-----------|----------|-------|-------|
| `--ink` (#F2EBDD) | `--parchment-100` (#1B1320) | Body text | 13.1:1 | ✅ AAA |
| `--ink` (#F2EBDD) | `--warm-white` (#261B2C) | Card body text | 10.6:1 | ✅ AAA |
| `--ink-muted` (#B9AEA0) | `--parchment-100` (#1B1320) | Secondary text | 7.8:1 | ✅ AAA |
| `#FFFFFF` | `--vermilion-600` (#E0674D) | Dark mode button | 3.2:1 | ✅ AA-large |
| `--jade-600` (#7FB095) | `--parchment-100` (#1B1320) | Positive status | 7.7:1 | ✅ AAA |
| `--amber-700` (#E2B25A) | `--parchment-100` (#1B1320) | Warning status | 8.9:1 | ✅ AAA |
| `--oxblood-700` (#E27C86) | `--parchment-100` (#1B1320) | Negative status | 6.6:1 | ✅ AA |

---

## Typography Quick Reference

| Token | Family | Weight | Use |
|-------|--------|--------|-----|
| Display | Fraunces (variable serif) | 600 | Hero H1, page titles |
| Heading | Manrope | 600–800 | Section headings, UI labels |
| Body | DM Sans | 400/500 | Paragraphs, descriptions |
| Telugu | Noto Sans Telugu | — | Telugu script (line-height 1.75) |
| Hindi | Noto Sans Devanagari | — | Hindi script (line-height 1.75) |

## Spacing Scale

| Token | rem | px |
|-------|-----|-----|
| `--space-1` | 0.25 | 4 |
| `--space-2` | 0.5 | 8 |
| `--space-3` | 0.75 | 12 |
| `--space-4` | 1 | 16 |
| `--space-6` | 1.5 | 24 |
| `--space-8` | 2 | 32 |
| `--space-12` | 3 | 48 |
| `--space-16` | 4 | 64 |
| `--space-20` | 5 | 80 |
| `--space-24` | 6 | 96 |
