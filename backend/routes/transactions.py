from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
from json_utils import decimal_safe_json

router = APIRouter(prefix="/transactions", tags=["transactions"])


class RelabelRequest(BaseModel):
    category_id: str


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
