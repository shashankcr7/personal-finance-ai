from datetime import date
from decimal import Decimal

from .utils import quantize


def get_goal_progress(goal: dict, current_value: Decimal, as_of: date) -> dict:
    target_amount = goal["target_amount"]
    days_remaining = (goal["target_date"] - as_of).days

    if days_remaining <= 0:
        projected_value = current_value
    else:
        years_remaining = Decimal(days_remaining) / Decimal("365.25")
        growth_rate = Decimal("1") + (goal["assumed_return"] / Decimal("100"))
        projected_value = current_value * (growth_rate**years_remaining)

    percent_funded = (
        current_value / target_amount * Decimal("100") if target_amount > 0 else Decimal("0")
    )

    return {
        "current_value": quantize(current_value),
        "projected_value": quantize(projected_value),
        "percent_funded": quantize(percent_funded),
        "on_track": projected_value >= target_amount,
        "assumed_return": goal["assumed_return"],
        "target_amount": target_amount,
        "target_date": goal["target_date"],
        "is_projection": True,
    }
