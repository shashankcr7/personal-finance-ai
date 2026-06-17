# CLAUDE.md — Project Context

Personal finance web app for one household (two users). Ingests statements, finds structural money leaks, reviews the portfolio against goals, and answers questions in plain language. **It never gives regulated investment advice.**

Read `/docs/PRD.md` for scope, `/docs/BUILD_SPEC.md` for the technical core, and `/docs/UI_SPEC.md` (+ `/docs/wireframes/*.png`) for screens.

## Stack
- **Frontend**: Next.js (TypeScript), Tailwind. Charts via a charting lib (recharts or chart.js).
- **Backend**: Python (FastAPI). All parsing and analytics live here.
- **DB**: Postgres (Supabase) with Row-Level Security.
- **AI**: Claude API, called **only** from the backend.
- **Deploy**: Vercel (frontend), Render (backend).

## Non-negotiable rules (do not violate, ever)
1. **The LLM never does arithmetic.** Every number shown to the user is computed by deterministic Python with unit tests. The LLM only categorizes text, parses intent, and narrates pre-computed numbers.
2. **Money is `Decimal` in Python and `NUMERIC` in Postgres. Never float.**
3. **Parse-then-delete.** Raw statement files (CAS PDF, bank CSV) are parsed in memory and deleted immediately. Never persist the raw file.
4. **No investment recommendations.** The app may *analyze* and *flag* (e.g. "this fund overlaps your holdings"); it must never say buy/sell/allocate a specific security. Surface assumptions; label projections as projections.
5. **Secrets in env vars, never committed.** The Claude API key is server-side only and must never reach the frontend bundle.
6. **RLS on every table**; each user sees only their rows. Auth allowlists the two household emails.
7. **No PAN stored.** The CAS password is supplied per-upload, held in memory, and discarded.

## Repo structure
```
/frontend        Next.js app
/backend         FastAPI app
  /parsers       cas_parser.py, bank_parser.py
  /analytics     deterministic functions (money math + leak detectors)
  /agent         Claude orchestration (summary builder + chat)
  /tests         golden tests for parsers, normalizer corpus, analytics units
/docs            PRD.md, BUILD_SPEC.md, UI_SPEC.md, /wireframes
CLAUDE.md
```

## How to work on this codebase
- **Use Plan mode** for anything in `/parsers`, `/analytics`, `/agent`, auth, or security. Review those diffs by hand. Auto-accept is only acceptable for UI scaffolding.
- **Build order**: parsers → analytics (with tests) → API → frontend → agent. Do not build the whole app in one pass; the money logic must be correct and tested before anything depends on it.
- **Tests first for analytics.** Every analytics function ships with unit tests using fixed fixtures. A function with no test is not done.
- **Definition of done (per module)**: lint passes; tests pass; no float used for money; no raw file persisted; no secret in code; LLM output is never used as a number.
