from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
from json_utils import decimal_safe_json

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str


@router.get("")
def list_categories(
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    rows = repository.fetch_categories(conn, user_id)
    return JSONResponse(content=decimal_safe_json(rows))


@router.post("")
def create_category(
    body: CategoryCreate,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    category_id = repository.create_category(conn, user_id, body.name)
    return JSONResponse(content=decimal_safe_json({"id": category_id}))
