# UI_SPEC — Screens, Components, States

Visual reference: `/docs/wireframes/*.png` (exported from Figma). This text spec is **authoritative** for components and behavior; the PNGs show layout intent. Fidelity is low (wireframe) — render real charts with the charting lib during build.

## Global
- Responsive **web** app (no native). Optional PWA.
- Left **sidebar** on all signed-in screens: app name, household label, nav items (Dashboard, Upload, Goals, Chat), active state highlighted.
- Money formatted in Indian style (lakh/crore, ₹). Decimals from the backend; never compute in the client.

## 1. Login
- Centered card: email field, password field, primary "Log in".
- Note: "Allowlisted accounts only · 2FA required".
- States: invalid credentials error; 2FA challenge.

## 2. Upload
- Three cards: **CAS PDF** (drop/browse + CAS password field), **Bank CSV/Excel** (drop/browse, ICICI·Kotak), **Loan — SBI** (manual form: original principal, outstanding, rate, EMI, tenure left, Save).
- **Recent uploads** list: type, period, parse status badge.
- Trust banner: "Raw statements are parsed, then deleted. Only structured data is stored."
- States: idle, parsing (spinner), parse error (bad password / unrecognized format, with retry), success.

## 3. Dashboard — monthly view
- Header: title, **view toggle (This month | All months)**, month selector.
- **KPI row** (4 cards, each with sparkline + MoM delta badge): Income, Expenses, Investments, Net worth.
- **Loan tracker card**: outstanding (large), rate · EMI, progress bar of % principal paid, years left.
- **Cash flow card**: income vs expense bars, "Saved ₹X (Y% of income)".
- **Spend by category**: horizontal bars, top categories.
- **Portfolio allocation**: donut (equity/debt/cash) + legend.
- **Leak tiles** ("Where you're losing money"): one compact tile per leak, rupee impact as the headline number, short detail below.
- States: first-run / no data (prompt to upload), partial data (some sources missing → show what's available, flag gaps).

## 4. Dashboard — Trends (all months)
- Reached via "All months" toggle.
- Summary stat chips: avg savings rate, 12-mo expense trend, net worth YoY.
- **Cash-flow line chart**: income, expense, savings on one shared axis (monthly), with legend and month labels. (Income and investments are intentionally NOT on the same axis — different magnitudes.)
- **Portfolio / net-worth growth**: bar (or line) over months, in ₹ lakh.
- State: insufficient history (< 2 months) → "Need a couple more months of data to show trends."

## 5. Goals
- Header: title, "+ Add goal".
- Subtitle: "Projections use your own return assumptions — shown and editable on each goal."
- Goal card: name, target amount · target date, **assumed-return pill (editable)**, progress bar + % funded, on-track / behind badge, edit · delete.
- Add/edit modal: name, target amount, target date, priority, assumed return, notes.
- States: empty (no goals → prompt), behind-goal emphasis.

## 6. Chat
- Message list: user bubbles (right), assistant bubbles (left).
- Input box + Send.
- Footer note: "Answers are grounded in your actual numbers. No buy/sell recommendations." and "The agent reads pre-computed numbers — it never does the math itself."
- States: thinking/streaming, error/retry. Assistant must decline buy/sell requests and restate it can analyze, not advise.
