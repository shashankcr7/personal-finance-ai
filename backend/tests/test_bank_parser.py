import io
from datetime import date
from decimal import Decimal

import pytest

from parsers.bank_parser import parse_bank_statement

# Shaped like a real ICICI net-banking export: search-criteria preamble
# rows above the real header, then transactions, then a documentation
# footer below — all fabricated data, no real account details.
ICICI_MESSY_CSV = (
    ",,,,,,\n"
    ",DETAILED STATEMENT,,,,,\n"
    ",Account Number,,FAKE123456 ( INR ) - JANE DOE,,,\n"
    ",Transaction Date from,,01/07/2024,to,31/07/2024,\n"
    ",S No.,Transaction Date,Transaction Remarks,Withdrawal Amount(INR),Deposit Amount(INR),Balance(INR)\n"
    ",1,01/07/2024,BIL/NEFT/123456789012/Fake Bill Payment/Acme Pvt Ltd,500.00,,10000.00\n"
    ",2,02/07/2024,MMT/IMPS/998877665544/Fake Salary Credit,,20000.00,30000.00\n"
    ",Legends Used in Account Statement,,,,,\n"
    ",1. BIL - Internet Bill payment,,,,,\n"
)


def test_parse_icici_messy_real_shaped_export():
    file_obj = io.BytesIO(ICICI_MESSY_CSV.encode())

    rows = parse_bank_statement(file_obj, "icici")

    assert rows == [
        {
            "txn_date": date(2024, 7, 1),
            "amount": Decimal("500.00"),
            "direction": "debit",
            "description": "BIL/NEFT/123456789012/Fake Bill Payment/Acme Pvt Ltd",
            "balance_after": Decimal("10000.00"),
        },
        {
            "txn_date": date(2024, 7, 2),
            "amount": Decimal("20000.00"),
            "direction": "credit",
            "description": "MMT/IMPS/998877665544/Fake Salary Credit",
            "balance_after": Decimal("30000.00"),
        },
    ]
    assert file_obj.closed
    for row in rows:
        assert isinstance(row["amount"], Decimal)
        assert isinstance(row["balance_after"], Decimal)


def test_parse_kotak():
    csv_text = (
        "Transaction Date,Description,Debit,Credit,Balance\n"
        "01-07-2024,ATM WITHDRAWAL,2000.00,,20000.00\n"
        "02-07-2024,SALARY CREDIT,,60000.00,80000.00\n"
    )
    file_obj = io.BytesIO(csv_text.encode())

    rows = parse_bank_statement(file_obj, "kotak")

    assert rows == [
        {
            "txn_date": date(2024, 7, 1),
            "amount": Decimal("2000.00"),
            "direction": "debit",
            "description": "ATM WITHDRAWAL",
            "balance_after": Decimal("20000.00"),
        },
        {
            "txn_date": date(2024, 7, 2),
            "amount": Decimal("60000.00"),
            "direction": "credit",
            "description": "SALARY CREDIT",
            "balance_after": Decimal("80000.00"),
        },
    ]


def test_unknown_bank_raises():
    with pytest.raises(ValueError):
        parse_bank_statement(io.BytesIO(b""), "sbi")
