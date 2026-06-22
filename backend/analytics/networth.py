from decimal import Decimal

from .utils import quantize


def get_net_worth(
    holdings: list[dict], bank_balances: list[Decimal], loans: list[dict]
) -> Decimal:
    holdings_value = sum((h["market_value"] for h in holdings), Decimal("0"))
    cash_value = sum(bank_balances, Decimal("0"))
    loan_outstanding = sum((loan["principal_outstanding"] for loan in loans), Decimal("0"))
    return quantize(holdings_value + cash_value - loan_outstanding)


def get_portfolio_allocation(holdings: list[dict], bank_balances: list[Decimal]) -> dict:
    equity = sum((h["market_value"] for h in holdings if h["category"] == "equity"), Decimal("0"))
    debt = sum((h["market_value"] for h in holdings if h["category"] == "debt"), Decimal("0"))
    other = sum((h["market_value"] for h in holdings if h["category"] == "other"), Decimal("0"))
    cash = sum(bank_balances, Decimal("0"))
    return {
        "equity": quantize(equity),
        "debt": quantize(debt),
        "other": quantize(other),
        "cash": quantize(cash),
    }
