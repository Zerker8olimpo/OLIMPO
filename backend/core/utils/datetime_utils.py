from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    """
    Ensure a datetime is timezone-aware in UTC.

    If the datetime is naive, assume UTC.
    If it has timezone, convert to UTC.
    """

    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)