from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

import auth
import db
import repository
import summary
from analytics.trends import get_monthly_trends
from json_utils import decimal_safe_json

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/monthly")
def dashboard_monthly(
    month: date = Query(...),
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    result = summary.build_financial_summary(conn, user_id, month)
    return JSONResponse(content=decimal_safe_json(result))


@router.get("/trends")
def dashboard_trends(
    months: int = Query(12, ge=1, le=60),
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    end_month = date.today().replace(day=1)
    month_range = summary.generate_month_range(end_month, months)
    start, _ = summary.month_bounds(month_range[0])
    end = date.today()

    transactions = repository.fetch_transactions(conn, user_id, start, end)
    monthly_snapshots = repository.fetch_monthly_snapshots(conn, user_id, since=month_range[0])

    result = get_monthly_trends(transactions, monthly_snapshots, month_range)
    return JSONResponse(content=decimal_safe_json(result))
