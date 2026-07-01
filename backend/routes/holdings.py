from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import auth
import db
import repository
from json_utils import decimal_safe_json

router = APIRouter(prefix="/holdings", tags=["holdings"])


@router.get("")
def list_holdings(
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    rows = repository.fetch_latest_holdings(conn, user_id)
    return JSONResponse(content=decimal_safe_json(rows))
