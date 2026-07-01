from datetime import date
from decimal import Decimal

import psycopg2.extras

DEFAULT_CATEGORIES = [
    "Salary",
    "Groceries",
    "Food & Dining",
    "Transport",
    "Bills & Utilities",
    "Rent/Housing",
    "Shopping",
    "Entertainment",
    "Health",
    "Investments",
    "Loan/EMI",
    "Subscriptions",
    "Transfers",
    "Other",
    "Uncategorized",
]


def _dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# --- accounts ---


def get_or_create_account(conn, user_id, account_type: str, institution_name: str):
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id FROM accounts WHERE user_id = %s AND type = %s AND institution_name = %s",
            (user_id, account_type, institution_name),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            "INSERT INTO accounts (user_id, type, institution_name) "
            "VALUES (%s, %s, %s) RETURNING id",
            (user_id, account_type, institution_name),
        )
        return cur.fetchone()["id"]


# --- holdings ---


def insert_holdings(conn, user_id, account_id, holdings: list[dict]) -> int:
    if not holdings:
        return 0
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO holdings
                (user_id, account_id, asset_type, isin, name, units, nav,
                 market_value, cost_value, as_of_date, category)
            VALUES %s
            """,
            [
                (
                    user_id,
                    account_id,
                    h["asset_type"],
                    h["isin"],
                    h["name"],
                    h["units"],
                    h["nav"],
                    h["market_value"],
                    h["cost_value"],
                    h["as_of_date"],
                    h["category"],
                )
                for h in holdings
            ],
        )
    return len(holdings)


def fetch_latest_holdings(conn, user_id) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT asset_type, isin, name, units, nav, market_value, cost_value,
                   as_of_date, category
            FROM holdings
            WHERE user_id = %s AND as_of_date = (
                SELECT MAX(as_of_date) FROM holdings WHERE user_id = %s
            )
            """,
            (user_id, user_id),
        )
        return [dict(row) for row in cur.fetchall()]


# --- transactions ---


def insert_transactions(conn, user_id, account_id, transactions: list[dict]) -> int:
    if not transactions:
        return 0
    with conn.cursor() as cur:
        inserted = psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO transactions
                (user_id, account_id, txn_date, amount, direction, description,
                 balance_after, merchant_normalized, ai_category_id, final_category_id)
            VALUES %s
            ON CONFLICT (account_id, txn_date, amount, description) DO NOTHING
            RETURNING id
            """,
            [
                (
                    user_id,
                    account_id,
                    t["txn_date"],
                    t["amount"],
                    t["direction"],
                    t["description"],
                    t.get("balance_after"),
                    t.get("merchant_normalized"),
                    t.get("ai_category_id"),
                    t.get("final_category_id"),
                )
                for t in transactions
            ],
            fetch=True,
        )
    return len(inserted)


def fetch_transactions(conn, user_id, start_date: date, end_date: date) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT t.id, t.txn_date, t.amount, t.direction, t.description,
                   t.merchant_normalized, t.final_category_id AS category_id,
                   COALESCE(c.name, 'Uncategorized') AS category,
                   a.institution_name AS bank
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            LEFT JOIN categories c ON c.id = t.final_category_id
            WHERE t.user_id = %s AND t.txn_date >= %s AND t.txn_date < %s
            ORDER BY t.txn_date
            """,
            (user_id, start_date, end_date),
        )
        return [dict(row) for row in cur.fetchall()]


def fetch_current_bank_balances(conn, user_id) -> list[Decimal]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (t.account_id) t.balance_after
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.user_id = %s AND a.type = 'bank' AND t.balance_after IS NOT NULL
            ORDER BY t.account_id, t.txn_date DESC, t.created_at DESC
            """,
            (user_id,),
        )
        return [row[0] for row in cur.fetchall()]


# --- statement uploads ---


def insert_statement_upload(
    conn,
    user_id,
    account_id,
    source_type: str,
    original_filename: str | None,
    status: str,
    error_message: str | None = None,
    as_of_date: date | None = None,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO statement_uploads
                (user_id, account_id, source_type, original_filename, status,
                 error_message, as_of_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, account_id, source_type, original_filename, status, error_message, as_of_date),
        )
        return cur.fetchone()[0]


def fetch_recent_uploads(conn, user_id, limit: int = 20) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, source_type, original_filename, status, error_message, "
            "as_of_date, created_at FROM statement_uploads "
            "WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]


# --- categories / category_rules ---


def ensure_default_categories(conn, user_id) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM categories WHERE user_id = %s", (user_id,))
        existing = {row[0] for row in cur.fetchall()}
        missing = [name for name in DEFAULT_CATEGORIES if name not in existing]
        if missing:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO categories (user_id, name) VALUES %s",
                [(user_id, name) for name in missing],
            )


def fetch_categories(conn, user_id) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, name, parent_id FROM categories WHERE user_id = %s", (user_id,)
        )
        return [dict(row) for row in cur.fetchall()]


def get_category_id_by_name(conn, user_id, name: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM categories WHERE user_id = %s AND lower(name) = lower(%s)",
            (user_id, name),
        )
        row = cur.fetchone()
        return row[0] if row else None


def create_category(conn, user_id, name: str) -> str:
    existing_id = get_category_id_by_name(conn, user_id, name)
    if existing_id is not None:
        return existing_id
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING id",
            (user_id, name),
        )
        return cur.fetchone()[0]


def fetch_category_rules(conn, user_id) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT merchant_normalized, category_id FROM category_rules WHERE user_id = %s",
            (user_id,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def fetch_recent_category_rules(conn, user_id, limit: int = 20) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT cr.merchant_normalized, c.name
            FROM category_rules cr
            JOIN categories c ON c.id = cr.category_id
            WHERE cr.user_id = %s
            ORDER BY cr.updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def upsert_category_rule(conn, user_id, merchant_normalized: str, category_id) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO category_rules (user_id, merchant_normalized, category_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, merchant_normalized)
            DO UPDATE SET category_id = EXCLUDED.category_id, updated_at = now()
            """,
            (user_id, merchant_normalized, category_id),
        )


def relabel_transaction(conn, user_id, txn_id, category_id) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT merchant_normalized FROM transactions WHERE id = %s AND user_id = %s",
            (txn_id, user_id),
        )
        row = cur.fetchone()
        if row is None:
            return 0
        merchant_normalized = row[0]

        if merchant_normalized is None:
            cur.execute(
                "UPDATE transactions SET final_category_id = %s WHERE id = %s AND user_id = %s",
                (category_id, txn_id, user_id),
            )
            return cur.rowcount

        upsert_category_rule(conn, user_id, merchant_normalized, category_id)
        cur.execute(
            "UPDATE transactions SET final_category_id = %s "
            "WHERE user_id = %s AND merchant_normalized = %s",
            (category_id, user_id, merchant_normalized),
        )
        return cur.rowcount


# --- loans ---


def fetch_loans(conn, user_id) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, account_id, original_principal, principal_outstanding, "
            "interest_rate, emi_amount, tenure_months_left, as_of_date "
            "FROM loans WHERE user_id = %s",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_loan(conn, user_id, loan_id) -> dict | None:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, account_id, original_principal, principal_outstanding, "
            "interest_rate, emi_amount, tenure_months_left, as_of_date "
            "FROM loans WHERE id = %s AND user_id = %s",
            (loan_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_loan(conn, user_id, account_id, fields: dict):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO loans
                (user_id, account_id, original_principal, principal_outstanding,
                 interest_rate, emi_amount, tenure_months_left, as_of_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                account_id,
                fields["original_principal"],
                fields["principal_outstanding"],
                fields["interest_rate"],
                fields["emi_amount"],
                fields["tenure_months_left"],
                fields["as_of_date"],
            ),
        )
        return cur.fetchone()[0]


def update_loan(conn, user_id, loan_id, fields: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE loans SET
                principal_outstanding = %s,
                interest_rate = %s,
                emi_amount = %s,
                tenure_months_left = %s,
                as_of_date = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                fields["principal_outstanding"],
                fields["interest_rate"],
                fields["emi_amount"],
                fields["tenure_months_left"],
                fields["as_of_date"],
                loan_id,
                user_id,
            ),
        )
        return cur.rowcount


# --- goals ---


def fetch_goals(conn, user_id) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, name, target_amount, target_date, priority, assumed_return, notes "
            "FROM goals WHERE user_id = %s",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def create_goal(conn, user_id, fields: dict):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO goals
                (user_id, name, target_amount, target_date, priority, assumed_return, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                fields["name"],
                fields["target_amount"],
                fields["target_date"],
                fields.get("priority"),
                fields["assumed_return"],
                fields.get("notes"),
            ),
        )
        return cur.fetchone()[0]


def update_goal(conn, user_id, goal_id, fields: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE goals SET
                name = %s, target_amount = %s, target_date = %s,
                priority = %s, assumed_return = %s, notes = %s, updated_at = now()
            WHERE id = %s AND user_id = %s
            """,
            (
                fields["name"],
                fields["target_amount"],
                fields["target_date"],
                fields.get("priority"),
                fields["assumed_return"],
                fields.get("notes"),
                goal_id,
                user_id,
            ),
        )
        return cur.rowcount


def delete_goal(conn, user_id, goal_id) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM goals WHERE id = %s AND user_id = %s", (goal_id, user_id))
        return cur.rowcount


# --- monthly snapshots ---


def fetch_monthly_snapshots(conn, user_id, since: date | None = None) -> list[dict]:
    with _dict_cursor(conn) as cur:
        if since:
            cur.execute(
                "SELECT month, net_worth, portfolio_value, total_invested "
                "FROM monthly_snapshots WHERE user_id = %s AND month >= %s ORDER BY month",
                (user_id, since),
            )
        else:
            cur.execute(
                "SELECT month, net_worth, portfolio_value, total_invested "
                "FROM monthly_snapshots WHERE user_id = %s ORDER BY month",
                (user_id,),
            )
        return [dict(row) for row in cur.fetchall()]


# --- chat messages ---


def insert_chat_message(conn, user_id, role: str, content: str) -> dict:
    # A POST /chat request inserts the user turn, calls Claude, then inserts the
    # assistant turn, all within one transaction — Postgres's now() is fixed for the
    # life of a transaction, so it would give both rows the exact same created_at.
    # clock_timestamp() advances in real time even mid-transaction, keeping turns in
    # correct chronological order for fetch_chat_history's ORDER BY.
    with _dict_cursor(conn) as cur:
        cur.execute(
            "INSERT INTO chat_messages (user_id, role, content, created_at) "
            "VALUES (%s, %s, %s, clock_timestamp()) "
            "RETURNING id, role, content, created_at",
            (user_id, role, content),
        )
        return dict(cur.fetchone())


def fetch_chat_history(conn, user_id, limit: int = 50) -> list[dict]:
    with _dict_cursor(conn) as cur:
        cur.execute(
            "SELECT id, role, content, created_at FROM ("
            "  SELECT id, role, content, created_at FROM chat_messages"
            "  WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT %s"
            ") recent ORDER BY created_at ASC, id ASC",
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
