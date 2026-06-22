from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
from analytics import networth
from analytics.goals import get_goal_progress
from json_utils import decimal_safe_json

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal
    target_date: date
    priority: str | None = None
    assumed_return: Decimal
    notes: str | None = None


class GoalUpdate(GoalCreate):
    pass


@router.get("")
def list_goals(
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    goal_rows = repository.fetch_goals(conn, user_id)
    holdings = repository.fetch_latest_holdings(conn, user_id)
    bank_balances = repository.fetch_current_bank_balances(conn, user_id)
    loans = repository.fetch_loans(conn, user_id)
    net_worth = networth.get_net_worth(holdings, bank_balances, loans)

    today = date.today()
    progress = [
        {
            "id": goal["id"],
            "name": goal["name"],
            "priority": goal["priority"],
            "notes": goal["notes"],
            **get_goal_progress(goal, net_worth, today),
        }
        for goal in goal_rows
    ]
    return JSONResponse(content=decimal_safe_json(progress))


@router.post("")
def create_goal(
    body: GoalCreate,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    goal_id = repository.create_goal(conn, user_id, body.model_dump())
    return JSONResponse(content=decimal_safe_json({"id": goal_id}))


@router.put("/{goal_id}")
def update_goal(
    goal_id: str,
    body: GoalUpdate,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    updated = repository.update_goal(conn, user_id, goal_id, body.model_dump())
    if updated == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return JSONResponse(content=decimal_safe_json({"updated": True}))


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: str,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    deleted = repository.delete_goal(conn, user_id, goal_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return JSONResponse(content=decimal_safe_json({"deleted": True}))
