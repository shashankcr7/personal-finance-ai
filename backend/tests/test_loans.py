from datetime import date
from decimal import Decimal

from analytics.loans import get_loan_status

LOAN = {
    "original_principal": Decimal("1000000.00"),
    "principal_outstanding": Decimal("600000.00"),
    "interest_rate": Decimal("8.50"),
    "emi_amount": Decimal("12000.00"),
    "tenure_months_left": 48,
    "as_of_date": date(2024, 6, 1),
}


def test_get_loan_status():
    result = get_loan_status(LOAN)
    assert result["outstanding"] == Decimal("600000.00")
    assert result["percent_principal_paid"] == Decimal("40.00")
    assert result["rate"] == Decimal("8.50")
    assert result["emi"] == Decimal("12000.00")
    assert result["months_left"] == 48


def test_get_loan_status_projects_payoff_slower_than_recorded_tenure():
    # At this EMI, real amortization (62 months) takes longer than the
    # recorded tenure_months_left (48) — both figures are surfaced as-is.
    result = get_loan_status(LOAN)
    assert result["projected_months_remaining"] == 62
    assert result["projected_payoff_date"] == date(2029, 8, 1)
    assert result["payoff_note"] is None


def test_get_loan_status_projects_payoff_faster_than_recorded_tenure():
    loan = dict(LOAN, emi_amount=Decimal("50000.00"))
    result = get_loan_status(loan)
    assert result["projected_months_remaining"] == 13
    assert result["projected_payoff_date"] == date(2025, 7, 1)
    assert result["payoff_note"] is None


def test_get_loan_status_flags_emi_that_never_amortizes():
    loan = dict(LOAN, interest_rate=Decimal("24.00"), emi_amount=Decimal("4000.00"))
    result = get_loan_status(loan)
    assert result["projected_months_remaining"] is None
    assert result["projected_payoff_date"] is None
    assert result["payoff_note"] is not None
