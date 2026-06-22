from datetime import date
from decimal import Decimal

from analytics.cashflow import get_cashflow, get_expense_by_category, get_income

TRANSACTIONS = [
    {
        "txn_date": date(2024, 6, 5),
        "amount": Decimal("50000.00"),
        "direction": "credit",
        "category": "Salary",
    },
    {
        "txn_date": date(2024, 6, 6),
        "amount": Decimal("15000.00"),
        "direction": "debit",
        "category": "Rent",
    },
    {
        "txn_date": date(2024, 6, 10),
        "amount": Decimal("5000.00"),
        "direction": "debit",
        "category": "Groceries",
    },
    {
        "txn_date": date(2024, 6, 12),
        "amount": Decimal("2000.00"),
        "direction": "debit",
        "category": "Groceries",
    },
    {
        "txn_date": date(2024, 7, 1),
        "amount": Decimal("9999.00"),
        "direction": "debit",
        "category": "Rent",
    },
    {
        "txn_date": date(2024, 6, 20),
        "amount": Decimal("1000.00"),
        "direction": "credit",
        "category": "Refund",
    },
]

MONTH = date(2024, 6, 1)


def test_get_income():
    assert get_income(TRANSACTIONS, MONTH) == Decimal("50000.00")


def test_get_expense_by_category():
    assert get_expense_by_category(TRANSACTIONS, MONTH) == {
        "Rent": Decimal("15000.00"),
        "Groceries": Decimal("7000.00"),
    }


def test_get_cashflow():
    assert get_cashflow(TRANSACTIONS, MONTH) == {
        "income": Decimal("50000.00"),
        "expense": Decimal("22000.00"),
        "saved": Decimal("28000.00"),
        "savings_rate": Decimal("56.00"),
    }


def test_get_cashflow_zero_income_does_not_crash():
    transactions = [
        {
            "txn_date": date(2024, 6, 6),
            "amount": Decimal("3000.00"),
            "direction": "debit",
            "category": "Rent",
        }
    ]
    result = get_cashflow(transactions, MONTH)
    assert result["income"] == Decimal("0.00")
    assert result["expense"] == Decimal("3000.00")
    assert result["saved"] == Decimal("-3000.00")
    assert result["savings_rate"] == Decimal("0")
