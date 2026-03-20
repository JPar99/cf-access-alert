"""Time conversion helpers — UTC to local display."""

from datetime import datetime, timezone


def utc_to_local(utc_str: str) -> str:
    """Convert a UTC ISO string to local time for display in logs."""
    try:
        utc_dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        return utc_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except (ValueError, TypeError):
        return utc_str


def format_event_time(created_at: str) -> str:
    """Convert UTC timestamp from CF API to local time string."""
    try:
        utc_dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        local_dt = utc_dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except (ValueError, TypeError):
        return created_at
