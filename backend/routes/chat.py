from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import db
import repository
from agent import chat as chat_agent
from json_utils import decimal_safe_json

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


@router.post("")
def post_chat(
    body: ChatRequest,
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    repository.insert_chat_message(conn, user_id, "user", body.message)
    response_text = chat_agent.chat(
        conn, user_id, body.message, [turn.model_dump() for turn in body.history]
    )
    repository.insert_chat_message(conn, user_id, "assistant", response_text)
    return JSONResponse(content=decimal_safe_json({"response": response_text}))


@router.get("/history")
def get_chat_history(
    user_id: str = Depends(auth.get_current_user),
    conn=Depends(db.get_db_connection),
):
    rows = repository.fetch_chat_history(conn, user_id, limit=50)
    history = [{"role": row["role"], "content": row["content"]} for row in rows]
    return JSONResponse(content=decimal_safe_json(history))
