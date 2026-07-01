from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
import summary
from json_utils import decimal_safe_json

router = APIRouter(prefix="/transactions", tags=["transactions"])


class RelabelRequest(BaseModel):
    category_id: str


@router.get("")
def list_transactions(
    month: date = Query(...),
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    start, end = summary.month_bounds(month)
    rows = repository.fetch_transactions(conn, user_id, start, end)
    return JSONResponse(content=decimal_safe_json(rows))


@router.post("/{txn_id}/relabel")
def relabel_transaction(
    txn_id: str,
    body: RelabelRequest,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    updated = repository.relabel_transaction(conn, user_id, txn_id, body.category_id)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return JSONResponse(content=decimal_safe_json({"updated_count": updated}))
