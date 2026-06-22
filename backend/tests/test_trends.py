from datetime import date
from decimal import Decimal

from analytics.trends import get_monthly_trends

TRANSACTIONS = [
    {
        "txn_date": date(2024, 5, 5),
        "amount": Decimal("40000.00"),
        "direction": "credit",
        "category": "Salary",
    },
    {
        "txn_date": date(2024, 5, 10),
        "amount": Decimal("10000.00"),
        "direction": "debit",
        "category": "Rent",
    },
    {
        "txn_date": date(2024, 6, 5),
        "amount": Decimal("45000.00"),
        "direction": "credit",
        "category": "Salary",
    },
    {
        "txn_date": date(2024, 6, 10),
        "amount": Decimal("12000.00"),
        "direction": "debit",
        "category": "Rent",
    },
]
MONTHLY_SNAPSHOTS = [
    {
        "month": date(2024, 6, 1),
        "net_worth": Decimal("500000.00"),
        "portfolio_value": Decimal("350000.00"),
    }
]
MONTHS = [date(2024, 5, 1), date(2024, 6, 1)]


def test_get_monthly_trends():
    result = get_monthly_trends(TRANSACTIONS, MONTHLY_SNAPSHOTS, MONTHS)

    assert result == {
        "months": MONTHS,
        "income": [Decimal("40000.00"), Decimal("45000.00")],
        "expense": [Decimal("10000.00"), Decimal("12000.00")],
        "savings": [Decimal("30000.00"), Decimal("33000.00")],
        "net_worth": [None, Decimal("500000.00")],
        "portfolio_value": [None, Decimal("350000.00")],
    }
