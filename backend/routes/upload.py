from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import auth
import db
import repository
from agent.categorizer import categorize_unmatched
from json_utils import decimal_safe_json
from parsers.bank_parser import parse_bank_statement
from parsers.cas_parser import parse_cas
from parsers.merchant_normalizer import normalize_merchant

router = APIRouter(prefix="/upload", tags=["upload"])


def _bank_source_type(filename: str | None) -> str:
    if filename and filename.lower().endswith((".xls", ".xlsx")):
        return "bank_xlsx"
    return "bank_csv"


@router.post("/cas")
def upload_cas(
    file: UploadFile,
    password: str = Form(...),
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    account_id = repository.get_or_create_account(conn, user_id, "demat", "CAS Depository")

    try:
        holdings = parse_cas(file.file, password)
    except Exception as exc:
        repository.insert_statement_upload(
            conn, user_id, account_id, "cas", file.filename, "error", error_message=str(exc)
        )
        raise HTTPException(status_code=400, detail=f"Could not parse CAS file: {exc}")

    count = repository.insert_holdings(conn, user_id, account_id, holdings)
    as_of_date = holdings[0]["as_of_date"] if holdings else None
    repository.insert_statement_upload(
        conn, user_id, account_id, "cas", file.filename, "success", as_of_date=as_of_date
    )

    return JSONResponse(content=decimal_safe_json({"holdings_count": count}))


@router.post("/bank")
def upload_bank(
    file: UploadFile,
    bank: str = Form(...),
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    if bank not in ("icici", "kotak"):
        raise HTTPException(status_code=400, detail=f"Unsupported bank: {bank!r}")

    account_id = repository.get_or_create_account(conn, user_id, "bank", bank)
    source_type = _bank_source_type(file.filename)

    try:
        rows = parse_bank_statement(file.file, bank)
    except Exception as exc:
        repository.insert_statement_upload(
            conn, user_id, account_id, source_type, file.filename, "error", error_message=str(exc)
        )
        raise HTTPException(status_code=400, detail=f"Could not parse bank statement: {exc}")

    for row in rows:
        row["merchant_normalized"] = normalize_merchant(row["description"])

    repository.ensure_default_categories(conn, user_id)
    rules = repository.fetch_category_rules(conn, user_id)

    by_rule = 0
    unmatched_merchants = set()
    for row in rows:
        category_id = rules.get(row["merchant_normalized"])
        if category_id:
            row["final_category_id"] = category_id
            by_rule += 1
        else:
            unmatched_merchants.add(row["merchant_normalized"])

    by_ai = 0
    if unmatched_merchants:
        categories = repository.fetch_categories(conn, user_id)
        category_names = [c["name"] for c in categories]
        few_shot = repository.fetch_recent_category_rules(conn, user_id)

        guesses = categorize_unmatched(list(unmatched_merchants), category_names, few_shot)

        for merchant, category_name in guesses.items():
            if category_name is None:
                continue
            category_id = repository.get_category_id_by_name(conn, user_id, category_name)
            if category_id is None:
                continue
            repository.upsert_category_rule(conn, user_id, merchant, category_id)
            for row in rows:
                if row["merchant_normalized"] == merchant:
                    row["ai_category_id"] = category_id
                    row["final_category_id"] = category_id
                    by_ai += 1

    inserted = repository.insert_transactions(conn, user_id, account_id, rows)
    as_of_date = max((row["txn_date"] for row in rows), default=None)
    repository.insert_statement_upload(
        conn, user_id, account_id, source_type, file.filename, "success", as_of_date=as_of_date
    )

    uncategorized = len(rows) - by_rule - by_ai

    return JSONResponse(
        content=decimal_safe_json(
            {
                "transactions_inserted": inserted,
                "categorized_by_rule": by_rule,
                "categorized_by_ai": by_ai,
                "uncategorized": uncategorized,
            }
        )
    )
