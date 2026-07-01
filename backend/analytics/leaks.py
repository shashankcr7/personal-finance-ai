from datetime import date
from decimal import Decimal

from .utils import quantize

LEAK_THRESHOLDS = {
    "idle_cash_buffer": Decimal("100000"),
    "liquid_fund_yield_pct": Decimal("7.0"),
    "savings_account_yield_pct": Decimal("3.0"),
    "fund_category_keywords": [
        "FLEXI CAP",
        "LARGE CAP",
        "MID CAP",
        "SMALL CAP",
        "INDEX",
        "ELSS",
        "LIQUID",
    ],
    "regular_plan_keyword": "REGULAR",
    "regular_plan_expense_drag_pct": Decimal("1.0"),
    "high_interest_loan_threshold_pct": Decimal("8.0"),
    "subscription_min_occurrences": 3,
    "subscription_recency_window_days": 60,
    "subscription_excluded_categories": ["Transfers", "Loan/EMI"],
    "concentration_threshold_pct": Decimal("40.0"),
    "low_cash_buffer_months": Decimal("1.0"),
}


def _real_holdings(holdings: list[dict]) -> list[dict]:
    # "other" is currently only our own reconciliation line for CAS totals that
    # casparser couldn't break down by scheme — it isn't a real single fund, so
    # it shouldn't be judged as a concentration or cross-folio overlap.
    return [h for h in holdings if h["category"] != "other"]


def detect_idle_cash(bank_balances: list[Decimal], config: dict = LEAK_THRESHOLDS) -> dict | None:
    total_cash = sum(bank_balances, Decimal("0"))
    buffer = config["idle_cash_buffer"]
    if total_cash <= buffer:
        return None

    idle_amount = total_cash - buffer
    yield_gap = config["liquid_fund_yield_pct"] - config["savings_account_yield_pct"]
    rupee_impact = quantize(idle_amount * yield_gap / Decimal("100"))

    return {
        "leak_type": "idle_cash",
        "rupee_impact": rupee_impact,
        "detail": (
            f"₹{idle_amount:,.2f} held in bank accounts above a ₹{buffer:,.2f} buffer is "
            f"earning an estimated {config['savings_account_yield_pct']}% yield instead of a "
            f"{config['liquid_fund_yield_pct']}% benchmark — a gap of about "
            f"₹{rupee_impact:,.2f}/year."
        ),
    }


def detect_fund_overlap(holdings: list[dict], config: dict = LEAK_THRESHOLDS) -> dict | None:
    keyword_groups: dict[str, list[dict]] = {}
    for holding in holdings:
        if holding["asset_type"] != "mutual_fund" or not holding["name"]:
            continue
        name_upper = holding["name"].upper()
        for keyword in config["fund_category_keywords"]:
            if keyword in name_upper:
                keyword_groups.setdefault(keyword, []).append(holding)
                break

    overlaps = {keyword: funds for keyword, funds in keyword_groups.items() if len(funds) >= 2}
    if not overlaps:
        return None

    total_overlap_value = quantize(
        sum((h["market_value"] for funds in overlaps.values() for h in funds), Decimal("0"))
    )
    detail_parts = [
        f"{len(funds)} {keyword} funds (₹{quantize(sum((h['market_value'] for h in funds), Decimal('0'))):,.2f})"
        for keyword, funds in overlaps.items()
    ]

    return {
        "leak_type": "fund_overlap",
        "rupee_impact": total_overlap_value,
        "detail": "Holding overlapping fund categories: " + "; ".join(detail_parts) + ".",
    }


def detect_regular_vs_direct(
    holdings: list[dict], config: dict = LEAK_THRESHOLDS
) -> dict | None:
    regular_holdings = [
        h
        for h in holdings
        if h["asset_type"] == "mutual_fund"
        and h["name"]
        and config["regular_plan_keyword"] in h["name"].upper()
    ]
    if not regular_holdings:
        return None

    regular_value = sum((h["market_value"] for h in regular_holdings), Decimal("0"))
    rupee_impact = quantize(regular_value * config["regular_plan_expense_drag_pct"] / Decimal("100"))

    return {
        "leak_type": "regular_vs_direct",
        "rupee_impact": rupee_impact,
        "detail": (
            f"₹{regular_value:,.2f} held in regular-plan funds carries an estimated "
            f"{config['regular_plan_expense_drag_pct']}% higher annual expense ratio than the "
            f"direct-plan equivalent — about ₹{rupee_impact:,.2f}/year."
        ),
    }


def detect_high_interest_vs_low_return(
    loans: list[dict], bank_balances: list[Decimal], config: dict = LEAK_THRESHOLDS
) -> dict | None:
    high_interest_loans = [
        loan for loan in loans if loan["interest_rate"] > config["high_interest_loan_threshold_pct"]
    ]
    idle_cash = sum(bank_balances, Decimal("0"))
    if not high_interest_loans or idle_cash <= 0:
        return None

    worst_loan = max(high_interest_loans, key=lambda loan: loan["interest_rate"])
    comparable_amount = min(idle_cash, worst_loan["principal_outstanding"])
    rate_gap = worst_loan["interest_rate"] - config["savings_account_yield_pct"]
    rupee_impact = quantize(comparable_amount * rate_gap / Decimal("100"))

    return {
        "leak_type": "high_interest_vs_low_return",
        "rupee_impact": rupee_impact,
        "detail": (
            f"A loan at {worst_loan['interest_rate']}% interest is outstanding while "
            f"₹{idle_cash:,.2f} sits in low-yield bank balances — an estimated "
            f"₹{rupee_impact:,.2f}/year gap between the loan rate and the bank yield."
        ),
    }


def detect_isin_overlap(holdings: list[dict], config: dict = LEAK_THRESHOLDS) -> dict | None:
    groups: dict[str, list[dict]] = {}
    for holding in _real_holdings(holdings):
        isin = holding.get("isin")
        if not isin or isin.startswith("UNALLOCATED-"):
            continue
        groups.setdefault(isin, []).append(holding)

    overlaps = {isin: hs for isin, hs in groups.items() if len(hs) >= 2}
    if not overlaps:
        return None

    total_value = quantize(
        sum((h["market_value"] for hs in overlaps.values() for h in hs), Decimal("0"))
    )
    detail_parts = []
    for isin, hs in overlaps.items():
        names = "; ".join(f"{h['name']} (₹{h['market_value']:,.2f})" for h in hs)
        detail_parts.append(f"ISIN {isin} held via {len(hs)} folios: {names}")

    return {
        "leak_type": "isin_overlap",
        "rupee_impact": total_value,
        "detail": (
            "The same fund is split across multiple folios, which can complicate "
            "tracking and tax cost-basis calculations: " + "; ".join(detail_parts) + "."
        ),
    }


def detect_concentration_risk(
    holdings: list[dict], config: dict = LEAK_THRESHOLDS
) -> dict | None:
    real_holdings = _real_holdings(holdings)
    total_value = sum((h["market_value"] for h in real_holdings), Decimal("0"))
    if total_value <= 0:
        return None

    threshold = config["concentration_threshold_pct"]
    worst = max(real_holdings, key=lambda h: h["market_value"], default=None)
    if worst is None:
        return None

    share = worst["market_value"] / total_value * Decimal("100")
    if share <= threshold:
        return None

    return {
        "leak_type": "concentration_risk",
        "rupee_impact": quantize(worst["market_value"]),
        "detail": (
            f"{worst['name']} is ₹{worst['market_value']:,.2f} — "
            f"{quantize(share)}% of your tracked portfolio, above the "
            f"{threshold}% concentration flag."
        ),
    }


def detect_low_cash_buffer(
    bank_balances: list[Decimal],
    average_monthly_expense: Decimal,
    config: dict = LEAK_THRESHOLDS,
) -> dict | None:
    if average_monthly_expense <= 0:
        return None

    total_cash = sum(bank_balances, Decimal("0"))
    safe_buffer = quantize(average_monthly_expense * config["low_cash_buffer_months"])
    if total_cash >= safe_buffer:
        return None

    shortfall = quantize(safe_buffer - total_cash)
    return {
        "leak_type": "low_cash_buffer",
        "rupee_impact": shortfall,
        "detail": (
            f"₹{total_cash:,.2f} in bank balances is below a "
            f"{config['low_cash_buffer_months']}-month expense buffer of "
            f"₹{safe_buffer:,.2f} (based on recent average spend) — a shortfall of "
            f"about ₹{shortfall:,.2f}."
        ),
    }


def detect_unused_subscriptions(
    transactions: list[dict], as_of: date, config: dict = LEAK_THRESHOLDS
) -> dict | None:
    groups: dict[tuple[str, Decimal], list[dict]] = {}
    for txn in transactions:
        if txn["direction"] != "debit" or not txn.get("merchant_normalized"):
            continue
        # Recurring transfers/EMIs aren't subscriptions to reconsider cancelling —
        # exclude them so the heuristic doesn't flag a self-transfer as a leak.
        if txn.get("category") in config["subscription_excluded_categories"]:
            continue
        key = (txn["merchant_normalized"], txn["amount"])
        groups.setdefault(key, []).append(txn)

    flagged = []
    for (merchant, amount), txns in groups.items():
        if len(txns) < config["subscription_min_occurrences"]:
            continue
        last_txn_date = max(t["txn_date"] for t in txns)
        days_since_last = (as_of - last_txn_date).days
        if days_since_last >= config["subscription_recency_window_days"]:
            continue
        flagged.append((merchant, amount, len(txns)))

    if not flagged:
        return None

    annual_total = quantize(sum((amount * 12 for _, amount, _ in flagged), Decimal("0")))
    detail = "; ".join(
        f"{merchant} (₹{amount}/charge, {count} times seen)" for merchant, amount, count in flagged
    )

    return {
        "leak_type": "unused_subscriptions",
        "rupee_impact": annual_total,
        "detail": (
            "Recurring charges detected that may be worth reviewing for continued use: "
            f"{detail}. Flagged by recurrence pattern, not actual usage data."
        ),
    }
