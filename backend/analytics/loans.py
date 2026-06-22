from decimal import Decimal

from .utils import quantize


def get_loan_status(loan: dict) -> dict:
    original = loan["original_principal"]
    outstanding = loan["principal_outstanding"]
    percent_paid = (
        (original - outstanding) / original * Decimal("100") if original > 0 else Decimal("0")
    )
    return {
        "outstanding": quantize(outstanding),
        "percent_principal_paid": quantize(percent_paid),
        "rate": loan["interest_rate"],
        "emi": quantize(loan["emi_amount"]),
        "months_left": loan["tenure_months_left"],
    }
