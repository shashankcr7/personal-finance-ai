from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def decimal_safe_json(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {key: decimal_safe_json(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [decimal_safe_json(item) for item in obj]
    return obj
