from decimal import Decimal


def escape_like(s: str) -> str:
    """Escape SQL LIKE wildcard characters."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def to_decimal(val) -> Decimal:
    """Safely convert a SQL aggregate result (possibly None) to Decimal."""
    return Decimal(str(val)) if val else Decimal("0")
