from datetime import date
from decimal import Decimal

from casparser.enums import FileType
from casparser.types import (
    DematAccount,
    DematOwner,
    Equity,
    InvestorInfo,
    MutualFund,
    NSDLCASData,
    StatementPeriod,
)

from parsers.cas_parser import _holdings_from_nsdl_data


# Sum of the two valid entries below (15005.00 + 9740.42) — keeping the fixture's
# account.balance equal to this means no reconciliation gap by default.
ACCOUNTED_VALUE = Decimal("24745.42")


def _fixture_data(balance: Decimal = ACCOUNTED_VALUE) -> NSDLCASData:
    return NSDLCASData(
        accounts=[
            DematAccount(
                name="Demat Account",
                type="NSDL",
                folios=1,
                balance=balance,
                owners=[DematOwner(name="Test Investor", PAN="ABCDE1234F")],
                equities=[
                    Equity(
                        name="INFOSYS LTD",
                        isin="INE009A01021",
                        num_shares=Decimal("10"),
                        price=Decimal("1500.50"),
                        value=Decimal("15005.00"),
                    ),
                    Equity(
                        name="DELISTED CORP LTD",
                        isin="INE000000000",
                        num_shares=Decimal("5"),
                        price=Decimal("0"),
                        value=Decimal("12.34"),
                    ),
                ],
                mutual_funds=[
                    MutualFund(
                        name="PARAG PARIKH FLEXI CAP FUND",
                        isin="INF879O01019",
                        type="EQUITY",
                        balance=Decimal("123.456"),
                        nav=Decimal("78.9012"),
                        value=Decimal("9740.42"),
                        total_cost=Decimal("9000.00"),
                    ),
                    MutualFund(
                        name="TATA DIGITAL INDIA FUND",
                        isin="INF277K01Z77",
                        type="EQUITY",
                        balance=Decimal("1952.270"),
                        nav=Decimal("0"),
                        value=Decimal("46.16"),
                        total_cost=Decimal("70000.00"),
                    ),
                ],
            )
        ],
        statement_period=StatementPeriod(**{"from": "01-Jan-2024", "to": "30-Jun-2024"}),
        investor_info=InvestorInfo(
            name="Test Investor",
            email="test@example.com",
            address="Test Address",
            mobile="9999999999",
        ),
        file_type=FileType.NSDL,
    )


def test_holdings_from_nsdl_data():
    holdings = _holdings_from_nsdl_data(_fixture_data())

    # DELISTED CORP LTD (price=0) and TATA DIGITAL INDIA FUND (nav=0) must be
    # excluded — only the two valid entries should come through.
    assert holdings == [
        {
            "asset_type": "stock",
            "isin": "INE009A01021",
            "name": "INFOSYS LTD",
            "units": Decimal("10"),
            "nav": Decimal("1500.50"),
            "market_value": Decimal("15005.00"),
            "cost_value": None,
            "as_of_date": date(2024, 6, 30),
            "category": "equity",
        },
        {
            "asset_type": "mutual_fund",
            "isin": "INF879O01019",
            "name": "PARAG PARIKH FLEXI CAP FUND",
            "units": Decimal("123.456"),
            "nav": Decimal("78.9012"),
            "market_value": Decimal("9740.42"),
            "cost_value": Decimal("9000.00"),
            "as_of_date": date(2024, 6, 30),
            "category": "equity",
        },
    ]

    for holding in holdings:
        for field in ("units", "nav", "market_value"):
            assert isinstance(holding[field], Decimal)


def test_holdings_from_nsdl_data_adds_reconciliation_entry_for_unaccounted_balance():
    holdings = _holdings_from_nsdl_data(_fixture_data(balance=ACCOUNTED_VALUE + Decimal("5000.00")))

    assert len(holdings) == 3
    reconciliation = holdings[-1]
    assert reconciliation["category"] == "other"
    assert reconciliation["market_value"] == Decimal("5000.00")
    assert reconciliation["units"] == Decimal("0")
    assert reconciliation["nav"] == Decimal("0")
    assert "Demat Account" in reconciliation["name"]


def test_holdings_from_nsdl_data_skips_reconciliation_within_tolerance():
    holdings = _holdings_from_nsdl_data(_fixture_data(balance=ACCOUNTED_VALUE + Decimal("0.50")))

    assert len(holdings) == 2
