# Personal Finance AI

A privacy-first web app for one household: ingests bank, loan, and investment
statements, finds where money is structurally leaking, reviews the portfolio
against goals, and answers questions in plain language. **It never gives
regulated investment advice.**

## Docs
- `CLAUDE.md` — context + non-negotiable rules (read first)
- `docs/PRD.md` — scope, requirements, roadmap
- `docs/BUILD_SPEC.md` — parsers, normalizer, analytics, agent (the risky core)
- `docs/UI_SPEC.md` — screens, components, states
- `SETUP.md` — accounts, GitHub, env, and build order

## Stack
Next.js (TS) frontend · FastAPI (Python) backend · Postgres (Supabase) with RLS ·
Claude API server-side · Vercel + Render.

## Build order
Parsers → analytics (with tests) → API → frontend → agent. Money math is
deterministic and tested before anything depends on it. See `CLAUDE.md`.
