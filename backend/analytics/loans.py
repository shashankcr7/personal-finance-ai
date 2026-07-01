import calendar
from datetime import date
from decimal import ROUND_CEILING, Decimal

from .utils import quantize

NO_AMORTIZATION_NOTE = (
    "Current EMI does not cover monthly interest at this rate — "
    "outstanding principal will not decrease."
)


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _project_payoff(
    principal_outstanding: Decimal,
    interest_rate: Decimal,
    emi_amount: Decimal,
    as_of_date: date,
) -> tuple[int | None, date | None, str | None]:
    if principal_outstanding <= 0:
        return 0, as_of_date, None

    monthly_rate = interest_rate / Decimal("100") / Decimal("12")

    if monthly_rate == 0:
        months = int((principal_outstanding / emi_amount).to_integral_value(rounding=ROUND_CEILING))
        return months, _add_months(as_of_date, months), None

    if emi_amount <= principal_outstanding * monthly_rate:
        return None, None, NO_AMORTIZATION_NOTE

    # Standard amortization month-count formula, kept entirely in Decimal (via
    # Decimal.ln()) rather than float — this is a projection of a month count,
    # not a money amount, but CLAUDE.md's never-float rule is honored anyway.
    remaining_ratio = Decimal(1) - (monthly_rate * principal_outstanding / emi_amount)
    months_decimal = (-remaining_ratio.ln()) / (Decimal(1) + monthly_rate).ln()
    months = int(months_decimal.to_integral_value(rounding=ROUND_CEILING))
    return months, _add_months(as_of_date, months), None


def get_loan_status(loan: dict) -> dict:
    original = loan["original_principal"]
    outstanding = loan["principal_outstanding"]
    percent_paid = (
        (original - outstanding) / original * Decimal("100") if original > 0 else Decimal("0")
    )
    months, payoff_date, note = _project_payoff(
        outstanding, loan["interest_rate"], loan["emi_amount"], loan["as_of_date"]
    )
    return {
        "outstanding": quantize(outstanding),
        "percent_principal_paid": quantize(percent_paid),
        "rate": loan["interest_rate"],
        "emi": quantize(loan["emi_amount"]),
        "months_left": loan["tenure_months_left"],
        "projected_months_remaining": months,
        "projected_payoff_date": payoff_date,
        "payoff_note": note,
    }
