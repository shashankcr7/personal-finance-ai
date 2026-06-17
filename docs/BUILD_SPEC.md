# BUILD_SPEC — Parsing, Categorization, Analytics, Agent

The risky core. Build and test this before the UI. All money is `Decimal`.

## 1. Parsing

### 1.1 CAS (investments)
- Library: `casparser`. Input: password-protected CAS PDF (NSDL or CDSL). Password supplied per-upload, held in memory, discarded.
- Output per holding: `asset_type` (stock|mutual_fund), `isin`, `name`, `units`, `nav`, `market_value`, `cost_value` (detailed CAS only), `as_of_date`.
- One PAN-based CAS covers all stocks (Groww + Kite) and all mutual funds. Two people = two CAS files.
- Validate both NSDL and CDSL variants against a real sample before trusting the holdings model. Write a golden test per variant.

### 1.2 Bank (transactions)
- Library: `pandas` (+ `openpyxl` for .xlsx). Banks: ICICI, Kotak. Column layouts differ — keep a per-bank column map in config, not hardcoded.
- Normalize each row to: `txn_date`, `amount` (Decimal), `direction` (debit|credit), `description` (raw), `balance_after`.
- Dedupe on `(account_id, txn_date, amount, description)` so re-uploading an overlapping statement doesn't double-count.

### 1.3 Loan (manual)
- Form fields: `original_principal`, `principal_outstanding`, `interest_rate`, `emi_amount`, `tenure_months_left`, `as_of_date`. `original_principal` is required to compute % paid.

## 2. Merchant normalization (the hardest part — invest here)
Bank descriptions are noisy (`UPI/SWIGGY-1234/998877/PAYMENT`, `ACH/D/HDFCMF/...`). Goal: reduce a raw description to a stable `merchant_normalized` key.
- Pipeline: uppercase → strip transaction/ref IDs, dates, UPI handles, bank prefixes (UPI/IMPS/NEFT/ACH) via regex → collapse whitespace → extract the merchant token.
- Maintain a **test corpus**: real description → expected normalized key. This corpus is the spec; expand it whenever a new pattern appears. Normalizer quality determines whether rules match; treat regressions as bugs.

## 3. Categorization
Precedence (highest wins): **user final label > rule match (on `merchant_normalized`) > AI guess > "Uncategorized"**.
- **Rules layer (deterministic, first)**: `category_rules` keyed on `merchant_normalized`. Runs before any AI call.
- **Relabel → rule**: when a user relabels a transaction, upsert a rule for that `merchant_normalized` → category. Apply it to all past and future matching transactions.
- **AI fallback (only for unmatched)**: batch the unmatched descriptions to Claude with the category taxonomy and recent user corrections as few-shot examples. Returns a category per item, stored as `ai_category`. The LLM sees descriptions only — never amounts for computation.
- Accept that one merchant can legitimately be two categories; default at merchant level and let the user relabel specific exceptions. Do not build contextual categorization for v1.

## 4. Deterministic analytics (feed the dashboard AND the agent)
Each is pure, tested with fixtures, returns Decimals/structured data — never calls the LLM.
- `get_income(user, month)` — sum of credits categorized as income/salary.
- `get_expense_by_category(user, month)` — category → total.
- `get_cashflow(user, month)` → `{income, expense, saved, savings_rate}`.
- `get_net_worth(user, as_of)` = holdings market value + bank balances − loan outstanding.
- `get_portfolio_allocation(user, as_of)` → equity/debt/cash split by market value.
- `compute_xirr(cashflows)` — per holding and portfolio (P1, but design the cashflow store now).
- `get_loan_status(user)` → `{outstanding, percent_principal_paid, rate, emi, months_left}`.
- `get_monthly_trends(user, range)` → series for income, expense, savings, net worth.
- Leak detectors (each → `{leak_type, rupee_impact, detail}`), thresholds in config:
  - `detect_idle_cash` — savings balance above a buffer earning < liquid-fund yield.
  - `detect_fund_overlap` — funds sharing significant top holdings / same category duplication.
  - `detect_regular_vs_direct` — holdings in regular plans where a direct plan exists.
  - `detect_high_interest_vs_low_return` — loan rate > expected return on comparable low-return assets held.
  - `detect_unused_subscriptions` — recurring same-amount debits with no offsetting usage signal, dormant N+ days.

## 5. History persistence (for the Trends view)
- Derive monthly income/expense/savings from stored dated transactions.
- Portfolio/net-worth-over-time depends on point-in-time prices, so **write a `monthly_snapshots` row** (`user, month, net_worth, portfolio_value, total_invested`) at each CAS upload rather than trying to reconstruct historical NAVs.

## 6. Chat agent
- Build `financial_summary(user, month)` — a JSON object assembled purely from the analytics functions above (cashflow, allocation, goal progress, loan status, leaks, recent trends).
- Call Claude with: a system prompt stating the rules (no arithmetic, no buy/sell advice, state assumptions, only use provided numbers), the summary JSON, and the user's question.
- For two users the summary fits in context — **no RAG, no tool-calling, no vector DB for v1.**
- Persist turns in `chat_messages`. If a question needs a number not in the summary, extend the summary builder — never let the model compute it.

## 7. Testing checklist
- [ ] CAS golden tests: NSDL + CDSL sample → expected holdings.
- [ ] Bank parser tests: ICICI + Kotak sample → normalized transactions.
- [ ] Normalizer corpus passes; new patterns added as found.
- [ ] Each analytics function: unit test with fixed fixture and known expected Decimal.
- [ ] Each leak detector: positive + negative fixture.
- [ ] Agent: given a fixed summary, asserts it answers from provided numbers and refuses buy/sell asks.
