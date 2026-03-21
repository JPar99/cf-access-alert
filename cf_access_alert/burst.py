"""Burst detection — group rapid blocked events to avoid notification floods."""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from . import config

log = logging.getLogger("cf-access-alert")


class BurstTracker:
    """
    Track blocked events per IP within a sliding window.

    When the same IP produces >= BURST_THRESHOLD blocks within
    BURST_WINDOW seconds, suppress individual notifications and
    emit a single burst summary instead.
    """

    def __init__(self):
        # ip -> list of created_at timestamps (datetime objects)
        self._hits: dict[str, list[datetime]] = defaultdict(list)

    def _prune(self, ip: str, now: datetime) -> None:
        """Remove entries older than the burst window."""
        cutoff = now.timestamp() - config.BURST_WINDOW
        self._hits[ip] = [
            ts for ts in self._hits[ip] if ts.timestamp() > cutoff
        ]
        if not self._hits[ip]:
            del self._hits[ip]

    def record(self, event: dict) -> None:
        """Record a blocked event hit for its IP."""
        ip = event.get("ip_address", "unknown")
        try:
            created = datetime.strptime(
                event.get("created_at", ""), "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            created = datetime.now(timezone.utc)
        self._hits[ip].append(created)

    def classify(self, events: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Classify a batch of new blocked events into individual alerts
        and burst groups.

        Returns:
            (individual_events, burst_summaries)

        individual_events: events that should send a normal per-event alert.
        burst_summaries: synthetic event dicts summarizing a burst per IP.
            Each has keys: ip_address, count, emails, apps, countries,
            window_seconds, first_seen, last_seen.
        """
        now = datetime.now(timezone.utc)

        # Record all events first
        for ev in events:
            self.record(ev)

        # Group by IP
        by_ip: dict[str, list[dict]] = defaultdict(list)
        for ev in events:
            by_ip[ev.get("ip_address", "unknown")].append(ev)

        individual = []
        bursts = []

        for ip, ip_events in by_ip.items():
            self._prune(ip, now)
            hit_count = len(self._hits.get(ip, []))

            if hit_count >= config.BURST_THRESHOLD:
                # This IP is in burst mode — summarize instead of spamming
                emails = sorted(set(
                    ev.get("user_email", "unknown") for ev in ip_events
                ))
                apps = sorted(set(
                    ev.get("app_name", ev.get("app_domain", "unknown"))
                    for ev in ip_events
                ))
                countries = sorted(set(
                    ev.get("country", "unknown").upper() for ev in ip_events
                ))

                burst_summary = {
                    "_burst": True,
                    "ip_address": ip,
                    "count": hit_count,
                    "batch_count": len(ip_events),
                    "emails": emails,
                    "apps": apps,
                    "countries": countries,
                    "window_seconds": config.BURST_WINDOW,
                }

                log.warning(
                    "Burst detected: IP %s has %d blocked attempts in %s "
                    "(emails: %s, apps: %s)",
                    ip, hit_count, config.format_duration(config.BURST_WINDOW),
                    ", ".join(emails), ", ".join(apps),
                )
                bursts.append(burst_summary)
            else:
                individual.extend(ip_events)

        return individual, bursts