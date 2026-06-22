import json
from datetime import date

import json_utils
import summary

from .client import get_anthropic_client

CHAT_MODEL = "claude-sonnet-4-6"

# Capped to bound cost/latency, not for correctness — BUILD_SPEC notes that for two
# users the whole financial summary already fits in context with no RAG needed.
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT = (
    "You are a financial narration assistant for a household personal finance app. "
    "You are given a JSON object of pre-computed financial figures for the household. "
    "You must never perform arithmetic, and never recompute, estimate, or derive any "
    "number that is not already present in that JSON — only narrate the numbers given "
    "to you, in plain language. "
    "If answering the question would require a number not present in the JSON, say "
    "you don't have that figure yet rather than estimating or guessing it. "
    "You must never recommend buying, selling, or allocating to a specific security, "
    "fund, or asset class. You may analyze and flag things (for example, noting that a "
    "fund overlaps with the household's existing holdings) but you must never advise "
    "action on a specific instrument. "
    "If the user asks for investment advice or a buy/sell/allocate recommendation, "
    "decline explicitly and say that you can analyze their numbers but can't give "
    "investment advice. "
    "When the data includes an assumption (for example, a goal's assumed annual "
    "return), state that assumption explicitly. "
    "Label any forward-looking number as a projection, not a fact."
)


def financial_summary(conn, user_id, month: date) -> dict:
    raw = summary.build_financial_summary(conn, user_id, month)
    return json_utils.decimal_safe_json(raw)


def _build_messages(history: list[dict], message: str) -> list[dict]:
    valid_history = [
        {"role": turn["role"], "content": turn["content"]}
        for turn in history
        if turn.get("role") in ("user", "assistant")
    ]
    capped = valid_history[-MAX_HISTORY_MESSAGES:]
    return capped + [{"role": "user", "content": message}]


def chat(conn, user_id, message: str, history: list[dict]) -> str:
    month = date.today().replace(day=1)
    summary_text = json.dumps(financial_summary(conn, user_id, month))
    system = f"{SYSTEM_PROMPT}\n\nCurrent financial summary (JSON):\n{summary_text}"

    client = get_anthropic_client()
    response = client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        system=system,
        messages=_build_messages(history, message),
    )
    return response.content[0].text.strip()
