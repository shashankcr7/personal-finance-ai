from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
from json_utils import decimal_safe_json

router = APIRouter(prefix="/loan", tags=["loans"])


class LoanCreate(BaseModel):
    institution_name: str
    original_principal: Decimal
    principal_outstanding: Decimal
    interest_rate: Decimal
    emi_amount: Decimal
    tenure_months_left: int
    as_of_date: date


class LoanUpdate(BaseModel):
    principal_outstanding: Decimal
    interest_rate: Decimal
    emi_amount: Decimal
    tenure_months_left: int
    as_of_date: date


@router.post("")
def create_loan(
    body: LoanCreate,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    account_id = repository.get_or_create_account(conn, user_id, "loan", body.institution_name)
    loan_id = repository.create_loan(
        conn,
        user_id,
        account_id,
        {
            "original_principal": body.original_principal,
            "principal_outstanding": body.principal_outstanding,
            "interest_rate": body.interest_rate,
            "emi_amount": body.emi_amount,
            "tenure_months_left": body.tenure_months_left,
            "as_of_date": body.as_of_date,
        },
    )
    return JSONResponse(content=decimal_safe_json({"id": loan_id}))


@router.put("/{loan_id}")
def update_loan(
    loan_id: str,
    body: LoanUpdate,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    updated = repository.update_loan(
        conn,
        user_id,
        loan_id,
        {
            "principal_outstanding": body.principal_outstanding,
            "interest_rate": body.interest_rate,
            "emi_amount": body.emi_amount,
            "tenure_months_left": body.tenure_months_left,
            "as_of_date": body.as_of_date,
        },
    )
    if updated == 0:
        raise HTTPException(status_code=404, detail="Loan not found")
    return JSONResponse(content=decimal_safe_json({"updated": True}))
