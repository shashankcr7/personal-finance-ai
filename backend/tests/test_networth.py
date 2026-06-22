from decimal import Decimal

from analytics.networth import get_net_worth, get_portfolio_allocation

HOLDINGS = [
    {"asset_type": "stock", "category": "equity", "market_value": Decimal("100000.00")},
    {"asset_type": "mutual_fund", "category": "debt", "market_value": Decimal("50000.00")},
    {"asset_type": "mutual_fund", "category": "other", "market_value": Decimal("20000.00")},
]
BANK_BALANCES = [Decimal("30000.00"), Decimal("5000.00")]
LOANS = [{"principal_outstanding": Decimal("80000.00")}]


def test_get_net_worth():
    assert get_net_worth(HOLDINGS, BANK_BALANCES, LOANS) == Decimal("125000.00")


def test_get_portfolio_allocation():
    assert get_portfolio_allocation(HOLDINGS, BANK_BALANCES) == {
        "equity": Decimal("100000.00"),
        "debt": Decimal("50000.00"),
        "other": Decimal("20000.00"),
        "cash": Decimal("35000.00"),
    }
