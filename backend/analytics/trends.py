from datetime import date

from .cashflow import get_cashflow


def get_monthly_trends(
    transactions: list[dict], monthly_snapshots: list[dict], months: list[date]
) -> dict:
    snapshots_by_month = {
        (snapshot["month"].year, snapshot["month"].month): snapshot
        for snapshot in monthly_snapshots
    }

    income_series = []
    expense_series = []
    savings_series = []
    net_worth_series = []
    portfolio_value_series = []

    for month in months:
        cashflow = get_cashflow(transactions, month)
        income_series.append(cashflow["income"])
        expense_series.append(cashflow["expense"])
        savings_series.append(cashflow["saved"])

        snapshot = snapshots_by_month.get((month.year, month.month))
        net_worth_series.append(snapshot["net_worth"] if snapshot else None)
        portfolio_value_series.append(snapshot["portfolio_value"] if snapshot else None)

    return {
        "months": months,
        "income": income_series,
        "expense": expense_series,
        "savings": savings_series,
        "net_worth": net_worth_series,
        "portfolio_value": portfolio_value_series,
    }
