from datetime import date
from decimal import Decimal

from analytics.goals import get_goal_progress

AS_OF = date(2024, 1, 1)
CURRENT_VALUE = Decimal("1000000.00")
GOAL_BASE = {
    "target_date": date(2034, 1, 1),
    "assumed_return": Decimal("10.00"),
}


def test_get_goal_progress_on_track():
    goal = {**GOAL_BASE, "target_amount": Decimal("2000000.00")}

    result = get_goal_progress(goal, CURRENT_VALUE, AS_OF)

    assert result["current_value"] == Decimal("1000000.00")
    assert result["projected_value"] == Decimal("2594080.89")
    assert result["percent_funded"] == Decimal("50.00")
    assert result["on_track"] is True
    assert result["is_projection"] is True


def test_get_goal_progress_behind_target():
    goal = {**GOAL_BASE, "target_amount": Decimal("5000000.00")}

    result = get_goal_progress(goal, CURRENT_VALUE, AS_OF)

    assert result["projected_value"] == Decimal("2594080.89")
    assert result["percent_funded"] == Decimal("20.00")
    assert result["on_track"] is False


def test_get_goal_progress_target_date_already_past():
    goal = {
        "target_amount": Decimal("2000000.00"),
        "target_date": date(2023, 1, 1),
        "assumed_return": Decimal("10.00"),
    }

    result = get_goal_progress(goal, CURRENT_VALUE, AS_OF)

    assert result["projected_value"] == Decimal("1000000.00")
    assert result["on_track"] is False
