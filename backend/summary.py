from datetime import date
from decimal import Decimal

import repository
from analytics import cashflow, leaks, networth, trends
from analytics import goals as goals_analytics
from analytics import loans as loans_analytics
from analytics.utils import quantize

RECENT_TRENDS_MONTHS = 6


def month_bounds(month: date) -> tuple[date, date]:
    start = month.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def generate_month_range(end_month: date, count: int) -> list[date]:
    months = []
    year, month = end_month.year, end_month.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


def _previous_month(month: date) -> date:
    start = month.replace(day=1)
    if start.month == 1:
        return start.replace(year=start.year - 1, month=12)
    return start.replace(month=start.month - 1)


def _percent_change(current: Decimal, previous: Decimal | None) -> Decimal | None:
    if previous is None or previous == 0:
        return None
    return quantize((current - previous) / previous * Decimal("100"))


def build_financial_summary(conn, user_id, month: date) -> dict:
    start, end = month_bounds(month)
    transactions = repository.fetch_transactions(conn, user_id, start, end)
    holdings = repository.fetch_latest_holdings(conn, user_id)
    bank_balances = repository.fetch_current_bank_balances(conn, user_id)
    loan_rows = repository.fetch_loans(conn, user_id)
    goal_rows = repository.fetch_goals(conn, user_id)

    recent_months = generate_month_range(month, RECENT_TRENDS_MONTHS)
    recent_start, _ = month_bounds(recent_months[0])
    recent_transactions = repository.fetch_transactions(conn, user_id, recent_start, end)
    monthly_snapshots = repository.fetch_monthly_snapshots(conn, user_id, since=recent_months[0])

    cashflow_result = cashflow.get_cashflow(transactions, month)
    expense_by_category = cashflow.get_expense_by_category(transactions, month)
    net_worth = networth.get_net_worth(holdings, bank_balances, loan_rows)
    allocation = networth.get_portfolio_allocation(holdings, bank_balances)
    portfolio_value = quantize(allocation["equity"] + allocation["debt"] + allocation["other"])

    loan_statuses = [
        {"id": loan["id"], **loans_analytics.get_loan_status(loan)} for loan in loan_rows
    ]
    goal_progress = [
        goals_analytics.get_goal_progress(goal, net_worth, month) for goal in goal_rows
    ]

    leak_results = [
        leaks.detect_idle_cash(bank_balances),
        leaks.detect_fund_overlap(holdings),
        leaks.detect_regular_vs_direct(holdings),
        leaks.detect_high_interest_vs_low_return(loan_rows, bank_balances),
        leaks.detect_unused_subscriptions(recent_transactions, month),
    ]
    detected_leaks = [leak for leak in leak_results if leak is not None]

    recent_trends = trends.get_monthly_trends(
        recent_transactions, monthly_snapshots, recent_months
    )

    previous_month = _previous_month(month)
    previous_cashflow = cashflow.get_cashflow(recent_transactions, previous_month)
    previous_snapshot = next(
        (s for s in monthly_snapshots if s["month"] == previous_month), None
    )
    deltas = {
        "income_pct": _percent_change(cashflow_result["income"], previous_cashflow["income"]),
        "expense_pct": _percent_change(cashflow_result["expense"], previous_cashflow["expense"]),
        "net_worth_pct": _percent_change(
            net_worth, previous_snapshot["net_worth"] if previous_snapshot else None
        ),
        "portfolio_value_pct": _percent_change(
            portfolio_value,
            previous_snapshot["portfolio_value"] if previous_snapshot else None,
        ),
    }

    return {
        "cashflow": cashflow_result,
        "expense_by_category": expense_by_category,
        "net_worth": net_worth,
        "portfolio_value": portfolio_value,
        "portfolio_allocation": allocation,
        "loans": loan_statuses,
        "goals": goal_progress,
        "leaks": detected_leaks,
        "recent_trends": recent_trends,
        "deltas": deltas,
    }
