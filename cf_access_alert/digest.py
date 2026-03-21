"""Daily digest — accumulate blocked-event stats and send periodic summaries."""

import logging
from collections import Counter
from datetime import datetime, timezone

from . import config

log = logging.getLogger("cf-access-alert")


class DigestAccumulator:
    """
    Collects blocked-event statistics over a digest period.

    The accumulator is reset after each digest is sent. Stats are
    kept in memory only — if the container restarts mid-period the
    digest resets. The next_digest_at timestamp is persisted in state
    so the schedule survives restarts.
    """

    def __init__(self):
        self.total_blocked: int = 0
        self.total_bursts: int = 0
        self.emails: Counter = Counter()
        self.ips: Counter = Counter()
        self.apps: Counter = Counter()
        self.countries: Counter = Counter()

    def record_event(self, event: dict) -> None:
        """Record a single blocked event into the digest."""
        self.total_blocked += 1
        self.emails[event.get("user_email", "unknown")] += 1
        self.ips[event.get("ip_address", "unknown")] += 1
        app = event.get("app_name", event.get("app_domain", "unknown"))
        self.apps[app] += 1
        self.countries[event.get("country", "unknown").upper()] += 1

    def record_burst(self, burst: dict) -> None:
        """Record a burst summary into the digest."""
        self.total_bursts += 1
        self.total_blocked += burst.get("batch_count", 0)
        self.ips[burst["ip_address"]] += burst.get("count", 0)
        for email in burst.get("emails", []):
            self.emails[email] += 1
        for app in burst.get("apps", []):
            self.apps[app] += 1
        for country in burst.get("countries", []):
            self.countries[country] += 1

    def is_empty(self) -> bool:
        """True if no events have been recorded."""
        return self.total_blocked == 0

    def build_summary(self) -> dict:
        """
        Build a digest summary dict suitable for notification senders.

        Returns a dict with: total_blocked, total_bursts, top_emails,
        top_ips, top_apps, top_countries.
        """
        return {
            "_digest": True,
            "total_blocked": self.total_blocked,
            "total_bursts": self.total_bursts,
            "top_emails": self.emails.most_common(5),
            "top_ips": self.ips.most_common(5),
            "top_apps": self.apps.most_common(5),
            "top_countries": self.countries.most_common(5),
            "unique_ips": len(self.ips),
            "unique_emails": len(self.emails),
        }

    def reset(self) -> None:
        """Clear all accumulated stats."""
        self.total_blocked = 0
        self.total_bursts = 0
        self.emails.clear()
        self.ips.clear()
        self.apps.clear()
        self.countries.clear()


def compute_next_digest(now: datetime) -> datetime:
    """
    Compute the next digest time based on DIGEST_HOUR.

    If today's digest hour hasn't passed yet, schedule for today.
    Otherwise, schedule for tomorrow.
    """
    target = now.replace(
        hour=config.DIGEST_HOUR, minute=config.DIGEST_MINUTE, second=0, microsecond=0
    )
    if target <= now:
        from datetime import timedelta
        target += timedelta(days=1)
    return target


def is_digest_due(next_digest_at: str | None) -> bool:
    """Check if the current time has passed the next scheduled digest."""
    if not next_digest_at:
        return False
    try:
        target = datetime.strptime(
            next_digest_at, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= target
    except (ValueError, TypeError):
        return False