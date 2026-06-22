from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

import auth
import db
import main
import repository
from agent import chat as chat_agent


def _override_get_current_user(user_id):
    def _inner():
        return user_id

    return _inner


def _override_get_db_connection(connection):
    def _inner():
        yield connection

    return _inner


def _apply_overrides(conn, test_user_id):
    main.app.dependency_overrides[auth.get_current_user] = _override_get_current_user(
        test_user_id
    )
    main.app.dependency_overrides[db.get_db_connection] = _override_get_db_connection(conn)


def test_upload_bank_route_inserts_transactions(conn, test_user_id):
    _apply_overrides(conn, test_user_id)
    csv_text = (
        "Transaction Date,Description,Debit,Credit,Balance\n"
        "01-07-2024,ATM WITHDRAWAL,2000.00,,20000.00\n"
        "02-07-2024,SALARY CREDIT,,60000.00,80000.00\n"
    )

    try:
        client = TestClient(main.app)
        response = client.post(
            "/upload/bank",
            data={"bank": "kotak"},
            files={"file": ("statement.csv", csv_text, "text/csv")},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["transactions_inserted"] == 2


def test_dashboard_monthly_route_returns_decimal_safe_json(conn, test_user_id):
    repository.ensure_default_categories(conn, test_user_id)
    salary_id = repository.get_category_id_by_name(conn, test_user_id, "Salary")
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST ROUTE BANK")
    repository.insert_transactions(
        conn,
        test_user_id,
        account_id,
        [
            {
                "txn_date": date(2024, 6, 5),
                "amount": Decimal("30000.00"),
                "direction": "credit",
                "description": "TEST ROUTE SALARY",
                "balance_after": Decimal("30000.00"),
                "final_category_id": salary_id,
            }
        ],
    )

    _apply_overrides(conn, test_user_id)

    try:
        client = TestClient(main.app)
        response = client.get(
            "/dashboard/monthly",
            params={"month": "2024-06-01"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["cashflow"]["income"] == "30000.00"
    assert isinstance(body["cashflow"]["income"], str)
    assert isinstance(body["net_worth"], str)


def test_goals_route_includes_identifying_fields(conn, test_user_id):
    goal_id = repository.create_goal(
        conn,
        test_user_id,
        {
            "name": "TEST ROUTE GOAL",
            "target_amount": Decimal("1000000.00"),
            "target_date": date(2030, 1, 1),
            "priority": "high",
            "assumed_return": Decimal("8.00"),
            "notes": "a note",
        },
    )

    _apply_overrides(conn, test_user_id)

    try:
        client = TestClient(main.app)
        response = client.get("/goals", headers={"Authorization": "Bearer test-token"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    matching = [g for g in body if g["id"] == str(goal_id)]
    assert len(matching) == 1
    assert matching[0]["name"] == "TEST ROUTE GOAL"
    assert matching[0]["priority"] == "high"
    assert matching[0]["notes"] == "a note"
    assert matching[0]["is_projection"] is True


def test_post_chat_persists_both_turns_and_returns_response(monkeypatch, conn, test_user_id):
    monkeypatch.setattr(
        chat_agent, "chat", lambda conn, user_id, message, history: "fixed reply"
    )

    _apply_overrides(conn, test_user_id)
    try:
        client = TestClient(main.app)
        response = client.post(
            "/chat",
            json={"message": "Where am I losing money?", "history": []},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"response": "fixed reply"}

    rows = repository.fetch_chat_history(conn, test_user_id)
    assert [r["role"] for r in rows[-2:]] == ["user", "assistant"]
    assert rows[-2]["content"] == "Where am I losing money?"
    assert rows[-1]["content"] == "fixed reply"


def test_get_chat_history_returns_persisted_turns_oldest_first(conn, test_user_id):
    repository.insert_chat_message(conn, test_user_id, "user", "TEST HISTORY Q1")
    repository.insert_chat_message(conn, test_user_id, "assistant", "TEST HISTORY A1")

    _apply_overrides(conn, test_user_id)
    try:
        client = TestClient(main.app)
        response = client.get("/chat/history", headers={"Authorization": "Bearer test-token"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    tail = body[-2:]
    assert tail == [
        {"role": "user", "content": "TEST HISTORY Q1"},
        {"role": "assistant", "content": "TEST HISTORY A1"},
    ]
    assert set(tail[0].keys()) == {"role", "content"}


def test_get_chat_history_empty_for_new_user_returns_empty_list(conn):
    fresh_user_id = "00000000-0000-0000-0000-000000000000"
    _apply_overrides(conn, fresh_user_id)
    try:
        client = TestClient(main.app)
        response = client.get("/chat/history", headers={"Authorization": "Bearer test-token"})
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
