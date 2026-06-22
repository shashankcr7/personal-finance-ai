from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from json_utils import decimal_safe_json


def test_decimal_becomes_string():
    assert decimal_safe_json(Decimal("15000.00")) == "15000.00"


def test_uuid_becomes_string():
    value = UUID("12345678-1234-5678-1234-567812345678")
    assert decimal_safe_json(value) == "12345678-1234-5678-1234-567812345678"


def test_date_and_datetime_become_isoformat():
    assert decimal_safe_json(date(2024, 6, 1)) == "2024-06-01"
    assert decimal_safe_json(datetime(2024, 6, 1, 12, 30)) == "2024-06-01T12:30:00"


def test_nested_structure_fully_converted():
    data = {
        "amount": Decimal("500.00"),
        "as_of_date": date(2024, 6, 1),
        "items": [
            {"value": Decimal("1.23"), "name": "x"},
            {"value": Decimal("4.56"), "name": "y"},
        ],
        "plain": "untouched",
        "count": 3,
    }

    result = decimal_safe_json(data)

    assert result == {
        "amount": "500.00",
        "as_of_date": "2024-06-01",
        "items": [
            {"value": "1.23", "name": "x"},
            {"value": "4.56", "name": "y"},
        ],
        "plain": "untouched",
        "count": 3,
    }

    def assert_no_float(value):
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for v in value.values():
                assert_no_float(v)
        if isinstance(value, list):
            for v in value:
                assert_no_float(v)

    assert_no_float(result)
