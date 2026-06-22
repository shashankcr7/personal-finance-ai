from decimal import Decimal

from analytics.loans import get_loan_status

LOAN = {
    "original_principal": Decimal("1000000.00"),
    "principal_outstanding": Decimal("600000.00"),
    "interest_rate": Decimal("8.50"),
    "emi_amount": Decimal("12000.00"),
    "tenure_months_left": 48,
}


def test_get_loan_status():
    assert get_loan_status(LOAN) == {
        "outstanding": Decimal("600000.00"),
        "percent_principal_paid": Decimal("40.00"),
        "rate": Decimal("8.50"),
        "emi": Decimal("12000.00"),
        "months_left": 48,
    }
