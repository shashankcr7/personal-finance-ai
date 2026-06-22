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
}


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
