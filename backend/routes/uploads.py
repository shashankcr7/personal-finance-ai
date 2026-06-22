from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import auth
import db
import repository
from json_utils import decimal_safe_json

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("")
def list_recent_uploads(
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    uploads = repository.fetch_recent_uploads(conn, user_id)
    return JSONResponse(content=decimal_safe_json(uploads))
