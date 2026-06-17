# PRD — Personal Finance AI ("working title")

**Author:** Shashank Hiremath
**Status:** Draft v1 · Personal MVP scope
**One-liner:** A privacy-first web app that ingests your statements, finds where money is structurally leaking, reviews your portfolio against your goals, and lets you ask questions in plain language — without ever giving regulated investment advice.

---

## 1. Context & Problem

Indian households juggle data across multiple banks, brokers, and fund platforms, and the apps that consolidate it are mostly product distributors whose "advice" is conflicted by what they earn from selling you funds, insurance, or loans. The result: people see *spend pie charts* (a commodity) but never see the *structural* leaks that actually cost them — idle cash, expense-ratio drag, overlapping funds, regular-vs-direct plan loss, high-interest debt running alongside low-return investments, forgotten subscriptions, and tax inefficiency.

**Who:** Initially a single household (two users) with accounts across ICICI, Kotak, SBI (loan), Groww, and Kite. **Cost of not solving:** these leaks compound silently; a 0.5–1% annual drag on a portfolio is large over a decade, and nobody is incentivized to point it out.

---

## 2. Goals (outcomes, not features)

1. **Surface structural money leaks** the user did not already know about — measured by leaks found and acted on, not charts rendered.
2. **Answer "is my portfolio on track for my goals?"** with honest, assumption-visible projections — never a recommendation to buy/sell a specific security.
3. **Make monthly review take minutes, not hours** — from upload to a usable dashboard with minimal manual effort.
4. **Earn trust through data minimization** — the user can verify the app holds as little sensitive data as possible.

## 2a. Non-Goals (deliberately out of scope)

1. **Personalized investment recommendations** ("buy X, sell Y, invest ₹Z here"). This requires a SEBI Investment Adviser licence; the product stays on the analysis/education side of that line. *Rationale: legal exposure dwarfs the feature value at this stage.*
2. **Real-time / intraday portfolio tracking.** Monthly CAS cadence is sufficient for a review tool. *Rationale: live data needs paid broker APIs and solves a problem this user doesn't have.*
3. **Supporting every Indian bank.** Only ICICs/Kotak/SBI are parsed. *Rationale: parsing is bank-specific; breadth is a trap before depth works.*
4. **Native mobile app.** Responsive web (optionally a PWA). *Rationale: two codebases for a desktop-friendly monthly workflow is wasted effort.*
5. **Account Aggregator integration (now).** *Rationale: FIU status requires being a regulated entity; revisit only at the public-launch stage via a licensed partner.*

---

## 3. Key Product Decisions & Tradeoffs

*This is the section worth reading. Each is a real fork with a chosen side.*

| Decision | Chosen approach | Tradeoff accepted |
|---|---|---|
| Investment data ingestion | One PAN-based **Consolidated Account Statement (CAS)** covers all stocks (Groww + Kite) and all mutual funds in a single monthly file | Monthly cadence, not live; password-protected PDF parsing |
| Advice vs analysis | **Analysis only** — flag a fund as poorly fitting the portfolio, never recommend a trade | Less "magic"; stays clear of SEBI RIA regulation |
| AI vs math | **LLM never does arithmetic.** Deterministic code computes every number; the LLM only categorizes, parses intent, and narrates | More backend code; in exchange, no hallucinated financial figures |
| Categorization | **Deterministic rules first, AI fallback.** User relabels create a normalized-merchant rule that fixes that merchant past and future | Merchant-string normalization is the hard part to get right |
| Security posture | **Data minimization** — parse statements, store structured rows, delete raw files | Cannot re-derive from source later; must re-upload |
| Loan data | **Manual entry** of 4 fields | Tiny manual step vs a brittle parser for one quarterly PDF |
| Platform | **Web app**, not native | No app-store presence; fine for the use case |

---

## 4. Personas

- **Household member (primary).** Technically comfortable, wants honesty over hand-holding, reviews finances monthly, distrusts product-pushing apps.
- **Spouse (secondary).** Less interested in mechanics, wants the dashboard answer and to relabel the occasional miscategorized expense.

---

## 5. User Stories

**Ingestion**
- As a household member, I want to upload a CAS PDF and have my full portfolio parsed, so I don't reconcile three platforms by hand.
- As a household member, I want to upload a bank CSV and have transactions auto-categorized, so I see spend without manual tagging.
- As a household member, I want to enter loan details in a short form, so my debt is part of the picture without parsing a statement.

**Insight**
- As a household member, I want the app to flag structural leaks (idle cash, fund overlap, regular-plan drag), so I act on losses I couldn't see.
- As a household member, I want to see whether my portfolio is on track for each goal with the assumptions shown, so I trust the projection.
- As a household member, I want to see my income, expenses, and investments trended across all months, so I can tell whether things are improving or drifting.
- As a household member, I want a single loan tracker showing how much I've paid down and how long is left, so my debt isn't a blind spot.

**Goals & chat**
- As a household member, I want to add/edit/delete goals with my own return assumptions, so projections reflect my reality.
- As a household member, I want to ask "where am I losing money?" in plain language and get an answer grounded in my actual numbers.

**Correction & trust**
- As a spouse, I want to relabel a miscategorized transaction and have it stick for that merchant forever.
- As a household member, I want to know raw statements are deleted after parsing, so I trust the app with sensitive data.

---

## 6. Requirements

### Must-Have (P0)
- **CAS ingestion**: upload password-protected CAS PDF → structured holdings (ISIN, units, NAV, market value, cost where available).
  - *Given* a valid CAS and password, *when* uploaded, *then* holdings appear in the dashboard and the raw file is deleted after parsing.
- **Bank CSV ingestion + categorization**: ICICI/Kotak CSV → categorized transactions; rules-first, AI fallback; dedupe on re-upload.
- **Relabel → persistent rule**: relabeling writes a normalized-merchant rule that applies to past and future transactions.
- **Loan manual entry + tracker**: capture original principal, outstanding, rate, EMI, tenure-left; dashboard shows outstanding, % principal paid, and years left. *(Original principal is required to compute % paid — store it.)*
- **Income tracking**: derive monthly income from credit transactions categorized as income/salary; surface as a dashboard KPI with month-over-month delta.
- **Goals CRUD** with editable, visible return assumptions.
- **Dashboard (monthly view)**: KPI row (income, expenses, investments, net worth) each with sparkline + MoM delta; loan tracker card; cash-flow (income vs expense vs saved); spend-by-category; portfolio allocation; goal progress; leak tiles.
- **Trends (all-months view)**: historical series for income, expense, savings (shared axis) and portfolio/net-worth growth over time; toggled from the monthly dashboard. *Requires persisting monthly history (see Open Questions).*
- **Leak detection (v1 set)**: idle cash, duplicate/overlapping funds, regular-vs-direct plan, high-interest debt vs low-return assets, recurring subscriptions.
- **Chat agent**: answers grounded in a deterministically-computed summary; no arithmetic by the LLM.
- **Security baseline**: raw-file deletion, RLS per user, secrets in env, Claude key server-side only, money stored as decimal not float.

### Nice-to-Have (P1)
- Few-shot the agent with recent user corrections for better novel-description labeling.
- XIRR per holding and portfolio-level.
- Tax surfacing (LTCG/STCG realized, ELSS tracking).

### Future Considerations (P2)
- Account Aggregator ingestion via a licensed partner (public-launch stage).
- Email/n8n auto-ingest of statements (kills the manual upload step).
- Multi-household / sharing (would trigger access-control and data-fiduciary obligations under DPDP).

---

## 7. Architecture (overview)

- **Frontend**: React/Next.js (TypeScript) — upload, dashboard, chat, goals.
- **Backend**: Python (FastAPI) — parsing (`casparser`, `pandas`), all deterministic analytics, Claude orchestration.
- **Data**: Postgres (Supabase) with Row-Level Security; money as `NUMERIC`.
- **AI**: Claude API, server-side only. Pattern: deterministic summary → injected into context → Claude narrates.
- **Deploy**: Vercel (frontend) + Render (Python backend).

## 8. Security Model

- Parse-then-delete: no raw statements at rest.
- No PAN stored; CAS password entered per-upload and discarded.
- RLS isolates each user's rows; auth via managed provider with 2FA; email allowlist for the two users.
- Secrets in env, never committed. HTTPS everywhere (platform default).
- *Honest framing: the goal is a small breach payoff, not "unhackable" — no such state exists.*

---

## 9. Success Metrics

*Personal-stage signals (this is a 2-person tool, so vanity adoption metrics don't apply):*
- **Leading**: monthly review completed without abandoning mid-upload; ≥1 actionable leak surfaced per month in early months; categorization accuracy climbing toward ~90%+ as rules accumulate (hypothesis).
- **Lagging**: measurable reduction in identified leaks over 2–3 quarters; portfolio drift flagged before it compounds.

*If expanded publicly later:* activation (% who complete first upload + see a leak), retention (% returning month 2/3 — the known PFM kill-zone), and trust signals.

---

## 10. Roadmap (Now / Next / Later)

**Now (Phase 1 — personal MVP)**
- CAS parser + bank CSV parser + loan form
- Categorization engine (rules + AI fallback + relabel→rule)
- Dashboard (income, expenses, investments, net worth, loan tracker) + all-months trends view
- Goals CRUD
- v1 leak detection
- Chat agent over deterministic summary
- Security baseline

**Next (Phase 2 — depth)**
- XIRR, tax surfacing
- Few-shot corrections into agent
- Email/n8n auto-ingest (remove manual upload)

**Later (Phase 3 — only if going public)**
- AA via licensed partner; DPDP compliance; access controls
- Multi-household; hardened auth; security assessment

---

## 11. Open Questions

- **[Engineering]** Does `casparser` cleanly handle both your NSDL and CDSL CAS variants? (Blocking — validate with a real file before building the holdings model.)
- **[Engineering]** What exact columns do ICICI vs Kotak CSV exports give? (Blocking — drives the transaction schema and the normalizer.)
- **[Product]** What's the v1 leak list's priority order — which leak matters most to you specifically?
- **[Engineering]** How is monthly history persisted for the all-months trends view — derive on the fly from stored transactions + dated holdings, or write a `monthly_snapshots` table at each upload? (Blocking for the Trends view; affects schema. Leaning: derive where possible, snapshot net worth since it depends on point-in-time prices.)
- **[Legal, if public]** Where exactly does "flag a poorly-fitting fund" sit relative to SEBI RIA rules? (Non-blocking for personal use; blocking before public launch.)
