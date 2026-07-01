from datetime import date
from decimal import Decimal

import repository


def test_test_user_fixture_resolves(test_user_id):
    assert test_user_id


def test_get_or_create_account_is_idempotent(conn, test_user_id):
    first = repository.get_or_create_account(conn, test_user_id, "bank", "TEST ICICI")
    second = repository.get_or_create_account(conn, test_user_id, "bank", "TEST ICICI")
    assert first == second


def test_insert_holdings_and_fetch_latest(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "demat", "TEST CAS")
    older = [
        {
            "asset_type": "stock",
            "isin": "INE000A00001",
            "name": "OLD HOLDING",
            "units": Decimal("1"),
            "nav": Decimal("10.00"),
            "market_value": Decimal("10.00"),
            "cost_value": None,
            "as_of_date": date(2024, 1, 31),
            "category": "equity",
        }
    ]
    newer = [
        {
            "asset_type": "mutual_fund",
            "isin": "INF000A00002",
            "name": "NEW HOLDING",
            "units": Decimal("5.5"),
            "nav": Decimal("20.00"),
            "market_value": Decimal("110.00"),
            "cost_value": Decimal("100.00"),
            "as_of_date": date(2024, 2, 29),
            "category": "debt",
        }
    ]
    repository.insert_holdings(conn, test_user_id, account_id, older)
    repository.insert_holdings(conn, test_user_id, account_id, newer)

    latest = repository.fetch_latest_holdings(conn, test_user_id)

    assert len(latest) == 1
    assert latest[0]["name"] == "NEW HOLDING"
    assert latest[0]["market_value"] == Decimal("110.00")
    assert isinstance(latest[0]["market_value"], Decimal)


def test_insert_transactions_dedupes_on_conflict(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST DEDUPE BANK")
    txn = {
        "txn_date": date(2024, 6, 1),
        "amount": Decimal("500.00"),
        "direction": "debit",
        "description": "TEST DUPLICATE DESC",
        "balance_after": Decimal("1000.00"),
        "merchant_normalized": "TEST MERCHANT",
    }

    first_count = repository.insert_transactions(conn, test_user_id, account_id, [txn])
    second_count = repository.insert_transactions(conn, test_user_id, account_id, [txn])

    assert first_count == 1
    assert second_count == 0


def test_fetch_transactions_filters_by_month_and_resolves_category(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST FETCH BANK")
    repository.ensure_default_categories(conn, test_user_id)
    category_id = repository.get_category_id_by_name(conn, test_user_id, "Groceries")

    in_month = {
        "txn_date": date(2024, 6, 10),
        "amount": Decimal("250.00"),
        "direction": "debit",
        "description": "IN MONTH TXN",
        "merchant_normalized": "SOME MERCHANT",
        "final_category_id": category_id,
    }
    out_of_month = {
        "txn_date": date(2024, 7, 1),
        "amount": Decimal("999.00"),
        "direction": "debit",
        "description": "OUT OF MONTH TXN",
    }
    repository.insert_transactions(conn, test_user_id, account_id, [in_month, out_of_month])

    rows = repository.fetch_transactions(conn, test_user_id, date(2024, 6, 1), date(2024, 7, 1))

    assert len(rows) == 1
    assert rows[0]["description"] == "IN MONTH TXN"
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["category_id"] == category_id
    assert rows[0]["bank"] == "TEST FETCH BANK"
    assert isinstance(rows[0]["amount"], Decimal)


def test_fetch_current_bank_balances_uses_most_recent_transaction(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST BALANCE BANK")
    older = {
        "txn_date": date(2024, 6, 1),
        "amount": Decimal("100.00"),
        "direction": "debit",
        "description": "OLDER",
        "balance_after": Decimal("5000.00"),
    }
    newer = {
        "txn_date": date(2024, 6, 15),
        "amount": Decimal("200.00"),
        "direction": "debit",
        "description": "NEWER",
        "balance_after": Decimal("4800.00"),
    }
    repository.insert_transactions(conn, test_user_id, account_id, [older, newer])

    balances = repository.fetch_current_bank_balances(conn, test_user_id)

    assert Decimal("4800.00") in balances
    assert Decimal("5000.00") not in balances


def test_ensure_default_categories_is_idempotent(conn, test_user_id):
    repository.ensure_default_categories(conn, test_user_id)
    repository.ensure_default_categories(conn, test_user_id)

    categories = repository.fetch_categories(conn, test_user_id)
    names = [c["name"] for c in categories]

    assert names.count("Groceries") == 1
    assert set(repository.DEFAULT_CATEGORIES) <= set(names)


def test_create_category_creates_new(conn, test_user_id):
    category_id = repository.create_category(conn, test_user_id, "TEST CUSTOM CATEGORY")

    categories = repository.fetch_categories(conn, test_user_id)
    assert any(c["id"] == category_id and c["name"] == "TEST CUSTOM CATEGORY" for c in categories)


def test_create_category_returns_existing_id_for_repeat_name_case_insensitive(conn, test_user_id):
    first_id = repository.create_category(conn, test_user_id, "TEST REPEAT CATEGORY")
    second_id = repository.create_category(conn, test_user_id, "test repeat category")

    assert first_id == second_id
    categories = repository.fetch_categories(conn, test_user_id)
    assert sum(1 for c in categories if c["id"] == first_id) == 1


def test_relabel_transaction_reapplies_to_matching_merchant(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST RELABEL BANK")
    repository.ensure_default_categories(conn, test_user_id)
    old_category_id = repository.get_category_id_by_name(conn, test_user_id, "Other")
    new_category_id = repository.get_category_id_by_name(conn, test_user_id, "Subscriptions")

    txn_a = {
        "txn_date": date(2024, 5, 1),
        "amount": Decimal("199.00"),
        "direction": "debit",
        "description": "NETFLIX MAY",
        "merchant_normalized": "NETFLIX",
        "final_category_id": old_category_id,
    }
    txn_b = {
        "txn_date": date(2024, 6, 1),
        "amount": Decimal("199.00"),
        "direction": "debit",
        "description": "NETFLIX JUNE",
        "merchant_normalized": "NETFLIX",
        "final_category_id": old_category_id,
    }
    repository.insert_transactions(conn, test_user_id, account_id, [txn_a, txn_b])

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM transactions WHERE user_id = %s AND description = %s",
            (test_user_id, "NETFLIX JUNE"),
        )
        relabeled_txn_id = cur.fetchone()[0]

    updated_count = repository.relabel_transaction(
        conn, test_user_id, relabeled_txn_id, new_category_id
    )

    assert updated_count == 2

    rule = repository.fetch_category_rules(conn, test_user_id)
    assert rule["NETFLIX"] == new_category_id

    rows = repository.fetch_transactions(conn, test_user_id, date(2024, 5, 1), date(2024, 7, 1))
    assert all(row["category"] == "Subscriptions" for row in rows)


def test_loan_crud(conn, test_user_id):
    account_id = repository.get_or_create_account(conn, test_user_id, "loan", "TEST SBI")
    loan_fields = {
        "original_principal": Decimal("1000000.00"),
        "principal_outstanding": Decimal("800000.00"),
        "interest_rate": Decimal("8.50"),
        "emi_amount": Decimal("12000.00"),
        "tenure_months_left": 60,
        "as_of_date": date(2024, 6, 1),
    }
    loan_id = repository.create_loan(conn, test_user_id, account_id, loan_fields)

    fetched = repository.get_loan(conn, test_user_id, loan_id)
    assert fetched["principal_outstanding"] == Decimal("800000.00")

    repository.update_loan(
        conn,
        test_user_id,
        loan_id,
        {
            "principal_outstanding": Decimal("750000.00"),
            "interest_rate": Decimal("8.25"),
            "emi_amount": Decimal("12000.00"),
            "tenure_months_left": 58,
            "as_of_date": date(2024, 8, 1),
        },
    )

    updated = repository.get_loan(conn, test_user_id, loan_id)
    assert updated["principal_outstanding"] == Decimal("750000.00")
    assert updated["tenure_months_left"] == 58


def test_goal_crud(conn, test_user_id):
    goal_id = repository.create_goal(
        conn,
        test_user_id,
        {
            "name": "TEST GOAL",
            "target_amount": Decimal("2000000.00"),
            "target_date": date(2030, 1, 1),
            "priority": "high",
            "assumed_return": Decimal("10.00"),
            "notes": None,
        },
    )

    goals = repository.fetch_goals(conn, test_user_id)
    assert any(g["id"] == goal_id and g["name"] == "TEST GOAL" for g in goals)

    repository.update_goal(
        conn,
        test_user_id,
        goal_id,
        {
            "name": "TEST GOAL UPDATED",
            "target_amount": Decimal("2500000.00"),
            "target_date": date(2031, 1, 1),
            "priority": "medium",
            "assumed_return": Decimal("9.00"),
            "notes": "updated",
        },
    )
    goals = repository.fetch_goals(conn, test_user_id)
    updated = next(g for g in goals if g["id"] == goal_id)
    assert updated["name"] == "TEST GOAL UPDATED"
    assert updated["target_amount"] == Decimal("2500000.00")

    deleted_count = repository.delete_goal(conn, test_user_id, goal_id)
    assert deleted_count == 1
    goals = repository.fetch_goals(conn, test_user_id)
    assert not any(g["id"] == goal_id for g in goals)


def test_insert_and_fetch_statement_uploads(conn, test_user_id):
    # Note: all inserts in this test share one Postgres transaction, where
    # now() (and so created_at) is fixed for the whole transaction - so this
    # doesn't assert cross-row chronological ordering, only that every row's
    # own fields round-trip correctly. Real uploads are separate requests/
    # transactions, so created_at DESC ordering is meaningful in production.
    account_id = repository.get_or_create_account(conn, test_user_id, "bank", "TEST UPLOADS BANK")

    repository.insert_statement_upload(
        conn, test_user_id, account_id, "bank_csv", "old.csv", "success", as_of_date=date(2024, 5, 1)
    )
    repository.insert_statement_upload(
        conn, test_user_id, account_id, "bank_csv", "broken.csv", "error", error_message="bad password"
    )
    repository.insert_statement_upload(
        conn, test_user_id, account_id, "bank_csv", "new.csv", "success", as_of_date=date(2024, 6, 1)
    )

    uploads = repository.fetch_recent_uploads(conn, test_user_id)
    by_filename = {u["original_filename"]: u for u in uploads}

    assert set(by_filename) == {"old.csv", "broken.csv", "new.csv"}
    assert by_filename["broken.csv"]["status"] == "error"
    assert by_filename["broken.csv"]["error_message"] == "bad password"
    assert by_filename["new.csv"]["as_of_date"] == date(2024, 6, 1)


def test_fetch_monthly_snapshots_filters_by_since(conn, test_user_id):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO monthly_snapshots (user_id, month, net_worth, portfolio_value, total_invested) "
            "VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)",
            (
                test_user_id,
                date(2024, 4, 1),
                Decimal("100000.00"),
                Decimal("80000.00"),
                Decimal("70000.00"),
                test_user_id,
                date(2024, 6, 1),
                Decimal("120000.00"),
                Decimal("90000.00"),
                Decimal("70000.00"),
            ),
        )

    snapshots = repository.fetch_monthly_snapshots(conn, test_user_id, since=date(2024, 5, 1))

    assert len(snapshots) == 1
    assert snapshots[0]["month"] == date(2024, 6, 1)
    assert snapshots[0]["net_worth"] == Decimal("120000.00")
