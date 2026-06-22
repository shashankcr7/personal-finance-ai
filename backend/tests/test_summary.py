from datetime import date
from decimal import Decimal

import repository
import summary


def test_build_financial_summary(conn, test_user_id):
    month = date(2024, 6, 1)

    repository.ensure_default_categories(conn, test_user_id)
    salary_category_id = repository.get_category_id_by_name(conn, test_user_id, "Salary")
    groceries_category_id = repository.get_category_id_by_name(conn, test_user_id, "Groceries")

    bank_account_id = repository.get_or_create_account(
        conn, test_user_id, "bank", "TEST SUMMARY BANK"
    )
    repository.insert_transactions(
        conn,
        test_user_id,
        bank_account_id,
        [
            {
                "txn_date": date(2024, 5, 5),
                "amount": Decimal("40000.00"),
                "direction": "credit",
                "description": "TEST SALARY MAY",
                "balance_after": Decimal("40000.00"),
                "final_category_id": salary_category_id,
            },
            {
                "txn_date": date(2024, 6, 5),
                "amount": Decimal("50000.00"),
                "direction": "credit",
                "description": "TEST SALARY",
                "balance_after": Decimal("50000.00"),
                "final_category_id": salary_category_id,
            },
            {
                "txn_date": date(2024, 6, 10),
                "amount": Decimal("5000.00"),
                "direction": "debit",
                "description": "TEST GROCERIES",
                "balance_after": Decimal("45000.00"),
                "final_category_id": groceries_category_id,
            },
        ],
    )

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO monthly_snapshots (user_id, month, net_worth, portfolio_value, total_invested) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                test_user_id,
                date(2024, 5, 1),
                Decimal("-500000.00"),
                Decimal("80000.00"),
                Decimal("75000.00"),
            ),
        )

    demat_account_id = repository.get_or_create_account(
        conn, test_user_id, "demat", "TEST SUMMARY CAS"
    )
    repository.insert_holdings(
        conn,
        test_user_id,
        demat_account_id,
        [
            {
                "asset_type": "stock",
                "isin": "INE000A00099",
                "name": "TEST STOCK",
                "units": Decimal("10"),
                "nav": Decimal("10000.00"),
                "market_value": Decimal("100000.00"),
                "cost_value": None,
                "as_of_date": date(2024, 6, 1),
                "category": "equity",
            }
        ],
    )

    loan_account_id = repository.get_or_create_account(
        conn, test_user_id, "loan", "TEST SUMMARY SBI"
    )
    loan_id = repository.create_loan(
        conn,
        test_user_id,
        loan_account_id,
        {
            "original_principal": Decimal("1000000.00"),
            "principal_outstanding": Decimal("600000.00"),
            "interest_rate": Decimal("8.50"),
            "emi_amount": Decimal("12000.00"),
            "tenure_months_left": 48,
            "as_of_date": date(2024, 6, 1),
        },
    )

    repository.create_goal(
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

    result = summary.build_financial_summary(conn, test_user_id, month)

    assert result["cashflow"] == {
        "income": Decimal("50000.00"),
        "expense": Decimal("5000.00"),
        "saved": Decimal("45000.00"),
        "savings_rate": Decimal("90.00"),
    }
    assert result["net_worth"] == Decimal("100000.00") + Decimal("45000.00") - Decimal(
        "600000.00"
    )
    assert result["portfolio_allocation"]["equity"] == Decimal("100000.00")
    assert result["portfolio_value"] == Decimal("100000.00")

    assert result["deltas"]["income_pct"] == Decimal("25.00")
    assert result["deltas"]["portfolio_value_pct"] == Decimal("25.00")
    assert result["deltas"]["net_worth_pct"] == Decimal("-9.00")

    assert len(result["loans"]) == 1
    assert result["loans"][0]["outstanding"] == Decimal("600000.00")
    assert result["loans"][0]["id"] == loan_id

    assert len(result["goals"]) == 1
    assert result["goals"][0]["is_projection"] is True
    assert result["goals"][0]["target_amount"] == Decimal("2000000.00")

    assert isinstance(result["leaks"], list)

    assert result["recent_trends"]["months"] == [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
        date(2024, 4, 1),
        date(2024, 5, 1),
        date(2024, 6, 1),
    ]
    assert result["recent_trends"]["income"][-1] == Decimal("50000.00")
