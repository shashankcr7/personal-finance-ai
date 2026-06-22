from datetime import datetime
from decimal import Decimal

import pandas as pd

# Column names/date formats are best-effort from publicly documented
# ICICI/Kotak statement exports. ICICI's map is validated against a real
# export; Kotak's is not yet validated against a real file (see
# docs/PRD.md open questions). Adjust this dict once a real export is
# checked; nothing else in this module should need to change.
BANK_COLUMN_MAPS = {
    "icici": {
        "txn_date": "Transaction Date",
        "description": "Transaction Remarks",
        "debit": "Withdrawal Amount(INR)",
        "credit": "Deposit Amount(INR)",
        "balance_after": "Balance(INR)",
        "date_format": "%d/%m/%Y",
    },
    "kotak": {
        "txn_date": "Transaction Date",
        "description": "Description",
        "debit": "Debit",
        "credit": "Credit",
        "balance_after": "Balance",
        "date_format": "%d-%m-%Y",
    },
}


def parse_bank_statement(file_obj, bank: str) -> list[dict]:
    try:
        column_map = BANK_COLUMN_MAPS[bank]
    except KeyError:
        raise ValueError(
            f"Unknown bank: {bank!r}. Expected one of {list(BANK_COLUMN_MAPS)}."
        )

    try:
        raw = _read_raw(file_obj)
    finally:
        file_obj.close()

    header_idx = _find_header_row(raw, column_map)
    df = _slice_at_header(raw, header_idx)
    return _normalize_rows(df, column_map)


def _read_raw(file_obj) -> pd.DataFrame:
    readers = [
        lambda: pd.read_excel(file_obj, header=None, dtype=str, engine="openpyxl"),
        lambda: pd.read_excel(file_obj, header=None, dtype=str, engine="xlrd"),
        lambda: pd.read_csv(file_obj, header=None, dtype=str),
    ]
    last_error: Exception | None = None
    for read in readers:
        file_obj.seek(0)
        try:
            return read()
        except Exception as exc:  # noqa: BLE001 - cascading format detection
            last_error = exc
    raise ValueError(f"Could not read statement as Excel or CSV: {last_error}")


def _find_header_row(raw: pd.DataFrame, column_map: dict) -> int:
    expected = {
        column_map["txn_date"],
        column_map["description"],
        column_map["debit"],
        column_map["credit"],
        column_map["balance_after"],
    }
    for idx, row in raw.iterrows():
        values = {str(v).strip() for v in row if pd.notna(v)}
        if expected <= values:
            return idx
    raise ValueError("Could not locate the transaction table header row in the statement.")


def _slice_at_header(raw: pd.DataFrame, header_idx: int) -> pd.DataFrame:
    header = raw.iloc[header_idx]
    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = header
    return data.reset_index(drop=True)


def _to_decimal(value) -> Decimal | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    return Decimal(text)


def _normalize_rows(df: pd.DataFrame, column_map: dict) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        debit = _to_decimal(row[column_map["debit"]])
        credit = _to_decimal(row[column_map["credit"]])
        if debit:
            direction, amount = "debit", debit
        elif credit:
            direction, amount = "credit", credit
        else:
            continue

        txn_date = datetime.strptime(
            str(row[column_map["txn_date"]]).strip(), column_map["date_format"]
        ).date()

        rows.append(
            {
                "txn_date": txn_date,
                "amount": amount,
                "direction": direction,
                "description": str(row[column_map["description"]]).strip(),
                "balance_after": _to_decimal(row[column_map["balance_after"]]),
            }
        )
    return rows
