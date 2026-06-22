from datetime import date
from decimal import Decimal

from .utils import quantize

INCOME_CATEGORIES = {"income", "salary"}


def _in_month(txn: dict, month: date) -> bool:
    return txn["txn_date"].year == month.year and txn["txn_date"].month == month.month


def get_income(transactions: list[dict], month: date) -> Decimal:
    total = Decimal("0")
    for txn in transactions:
        if (
            _in_month(txn, month)
            and txn["direction"] == "credit"
            and txn["category"].strip().lower() in INCOME_CATEGORIES
        ):
            total += txn["amount"]
    return quantize(total)


def get_expense_by_category(transactions: list[dict], month: date) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for txn in transactions:
        if _in_month(txn, month) and txn["direction"] == "debit":
            totals[txn["category"]] = totals.get(txn["category"], Decimal("0")) + txn["amount"]
    return {category: quantize(total) for category, total in totals.items()}


def get_cashflow(transactions: list[dict], month: date) -> dict:
    income = get_income(transactions, month)
    expense_by_category = get_expense_by_category(transactions, month)
    expense = quantize(sum(expense_by_category.values(), Decimal("0")))
    saved = quantize(income - expense)
    savings_rate = quantize(saved / income * Decimal("100")) if income > 0 else Decimal("0")
    return {
        "income": income,
        "expense": expense,
        "saved": saved,
        "savings_rate": savings_rate,
    }
