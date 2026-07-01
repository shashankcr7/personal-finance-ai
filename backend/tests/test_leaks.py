from datetime import date
from decimal import Decimal

from analytics.leaks import (
    detect_concentration_risk,
    detect_fund_overlap,
    detect_high_interest_vs_low_return,
    detect_idle_cash,
    detect_isin_overlap,
    detect_low_cash_buffer,
    detect_regular_vs_direct,
    detect_unused_subscriptions,
)


def test_detect_idle_cash_positive():
    result = detect_idle_cash([Decimal("150000.00"), Decimal("80000.00")])

    assert result is not None
    assert result["leak_type"] == "idle_cash"
    assert result["rupee_impact"] == Decimal("5200.00")


def test_detect_idle_cash_negative():
    result = detect_idle_cash([Decimal("50000.00"), Decimal("20000.00")])

    assert result is None


def test_detect_fund_overlap_positive():
    holdings = [
        {"asset_type": "mutual_fund", "name": "PPFAS FLEXI CAP FUND", "market_value": Decimal("50000.00")},
        {"asset_type": "mutual_fund", "name": "HDFC FLEXI CAP FUND", "market_value": Decimal("30000.00")},
    ]

    result = detect_fund_overlap(holdings)

    assert result is not None
    assert result["leak_type"] == "fund_overlap"
    assert result["rupee_impact"] == Decimal("80000.00")


def test_detect_fund_overlap_negative():
    holdings = [
        {"asset_type": "mutual_fund", "name": "PPFAS FLEXI CAP FUND", "market_value": Decimal("50000.00")},
        {"asset_type": "mutual_fund", "name": "UTI NIFTY INDEX FUND", "market_value": Decimal("30000.00")},
    ]

    result = detect_fund_overlap(holdings)

    assert result is None


def test_detect_regular_vs_direct_positive():
    holdings = [
        {"asset_type": "mutual_fund", "name": "ABC FUND REGULAR PLAN", "market_value": Decimal("60000.00")},
    ]

    result = detect_regular_vs_direct(holdings)

    assert result is not None
    assert result["leak_type"] == "regular_vs_direct"
    assert result["rupee_impact"] == Decimal("600.00")


def test_detect_regular_vs_direct_negative():
    holdings = [
        {"asset_type": "mutual_fund", "name": "ABC FUND DIRECT PLAN", "market_value": Decimal("60000.00")},
    ]

    result = detect_regular_vs_direct(holdings)

    assert result is None


def test_detect_high_interest_vs_low_return_positive():
    loans = [{"interest_rate": Decimal("12.00"), "principal_outstanding": Decimal("200000.00")}]
    bank_balances = [Decimal("50000.00")]

    result = detect_high_interest_vs_low_return(loans, bank_balances)

    assert result is not None
    assert result["leak_type"] == "high_interest_vs_low_return"
    assert result["rupee_impact"] == Decimal("4500.00")


def test_detect_high_interest_vs_low_return_negative():
    loans = [{"interest_rate": Decimal("7.00"), "principal_outstanding": Decimal("200000.00")}]
    bank_balances = [Decimal("50000.00")]

    result = detect_high_interest_vs_low_return(loans, bank_balances)

    assert result is None


def test_detect_unused_subscriptions_positive():
    as_of = date(2024, 6, 30)
    transactions = [
        {
            "txn_date": date(2024, 4, 15),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "merchant_normalized": "NETFLIX",
            "category": "Subscriptions",
        },
        {
            "txn_date": date(2024, 5, 15),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "merchant_normalized": "NETFLIX",
            "category": "Subscriptions",
        },
        {
            "txn_date": date(2024, 6, 15),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "merchant_normalized": "NETFLIX",
            "category": "Subscriptions",
        },
    ]

    result = detect_unused_subscriptions(transactions, as_of)

    assert result is not None
    assert result["leak_type"] == "unused_subscriptions"
    assert result["rupee_impact"] == Decimal("6000.00")


def test_detect_unused_subscriptions_negative_too_few_occurrences():
    as_of = date(2024, 6, 30)
    transactions = [
        {
            "txn_date": date(2024, 5, 15),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "merchant_normalized": "NETFLIX",
        },
        {
            "txn_date": date(2024, 6, 15),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "merchant_normalized": "NETFLIX",
        },
    ]

    result = detect_unused_subscriptions(transactions, as_of)

    assert result is None


def test_detect_unused_subscriptions_excludes_transfers():
    as_of = date(2026, 5, 31)
    transactions = [
        {
            "txn_date": date(2026, 5, 3),
            "amount": Decimal("20000.00"),
            "direction": "debit",
            "merchant_normalized": "SHASHANK S KKBK0000958",
            "category": "Transfers",
        },
        {
            "txn_date": date(2026, 5, 11),
            "amount": Decimal("20000.00"),
            "direction": "debit",
            "merchant_normalized": "SHASHANK S KKBK0000958",
            "category": "Transfers",
        },
        {
            "txn_date": date(2026, 5, 31),
            "amount": Decimal("20000.00"),
            "direction": "debit",
            "merchant_normalized": "SHASHANK S KKBK0000958",
            "category": "Transfers",
        },
    ]

    result = detect_unused_subscriptions(transactions, as_of)

    assert result is None


def test_detect_isin_overlap_positive():
    holdings = [
        {
            "isin": "INF879O01027",
            "name": "PPFAS MUTUAL FUND",
            "market_value": Decimal("4934.15"),
            "category": "equity",
        },
        {
            "isin": "INF879O01027",
            "name": "Parag Parikh Flexi Cap Fund - Direct Plan Growth",
            "market_value": Decimal("121731.11"),
            "category": "equity",
        },
        {
            "isin": "INE009A01021",
            "name": "INFOSYS LTD",
            "market_value": Decimal("5798.75"),
            "category": "equity",
        },
    ]

    result = detect_isin_overlap(holdings)

    assert result is not None
    assert result["leak_type"] == "isin_overlap"
    assert result["rupee_impact"] == Decimal("126665.26")


def test_detect_isin_overlap_negative_distinct_isins():
    holdings = [
        {"isin": "INF879O01027", "name": "FUND A", "market_value": Decimal("1000.00"), "category": "equity"},
        {"isin": "INE009A01021", "name": "FUND B", "market_value": Decimal("2000.00"), "category": "equity"},
    ]

    assert detect_isin_overlap(holdings) is None


def test_detect_isin_overlap_excludes_other_category_and_unallocated():
    holdings = [
        {
            "isin": "UNALLOCATED-Mutual Fund Folios",
            "name": "Unidentified holdings in Mutual Fund Folios",
            "market_value": Decimal("216829.32"),
            "category": "other",
        },
        {
            "isin": "UNALLOCATED-Mutual Fund Folios",
            "name": "Unidentified holdings in Mutual Fund Folios (2)",
            "market_value": Decimal("100.00"),
            "category": "other",
        },
    ]

    assert detect_isin_overlap(holdings) is None


def test_detect_concentration_risk_positive():
    holdings = [
        {"name": "BIG FUND", "market_value": Decimal("90000.00"), "category": "equity"},
        {"name": "SMALL FUND", "market_value": Decimal("10000.00"), "category": "equity"},
    ]

    result = detect_concentration_risk(holdings)

    assert result is not None
    assert result["leak_type"] == "concentration_risk"
    assert result["rupee_impact"] == Decimal("90000.00")


def test_detect_concentration_risk_negative_evenly_split():
    # 5 holdings at 20% each — no single one crosses the 40% threshold.
    holdings = [
        {"name": f"FUND {i}", "market_value": Decimal("20000.00"), "category": "equity"}
        for i in range(5)
    ]

    assert detect_concentration_risk(holdings) is None


def test_detect_concentration_risk_excludes_other_category():
    holdings = [
        {"name": "FUND A", "market_value": Decimal("30000.00"), "category": "equity"},
        {"name": "FUND B", "market_value": Decimal("30000.00"), "category": "equity"},
        {"name": "FUND C", "market_value": Decimal("30000.00"), "category": "equity"},
        {
            "name": "Unidentified holdings in Mutual Fund Folios",
            "market_value": Decimal("200000.00"),
            "category": "other",
        },
    ]

    # The reconciliation line dwarfs the real holdings — if it were included in
    # the total or treated as a candidate, this would (wrongly) flag. Each real
    # holding is an even 33% of the real-only total, below the 40% threshold.
    assert detect_concentration_risk(holdings) is None


def test_detect_low_cash_buffer_positive():
    result = detect_low_cash_buffer([Decimal("20000.00")], Decimal("50000.00"))

    assert result is not None
    assert result["leak_type"] == "low_cash_buffer"
    assert result["rupee_impact"] == Decimal("30000.00")


def test_detect_low_cash_buffer_negative_ample_cash():
    result = detect_low_cash_buffer([Decimal("100000.00")], Decimal("50000.00"))

    assert result is None


def test_detect_low_cash_buffer_negative_no_expense_history():
    result = detect_low_cash_buffer([Decimal("0.00")], Decimal("0.00"))

    assert result is None
