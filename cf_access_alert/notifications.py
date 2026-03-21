"""Notification dispatcher — routes alerts to all active channels.

Channel implementations live in the ``channels/`` package. This module
provides the same public API consumed by ``main.py``:

- ``verify_channels()``
- ``notify(event, shutdown)``
- ``notify_burst(burst, shutdown)``
- ``notify_digest(digest, shutdown)``
"""

import logging

from .channels import get_active_channels, ALL_CHANNELS
from .config import format_duration
from .timeutil import format_event_time

log = logging.getLogger("cf-access-alert")


# ---------------------------------------------------------------------------
# Startup verification
# ---------------------------------------------------------------------------

def verify_channels() -> bool:
    """Verify all enabled notification channels on startup.

    Logs status for every channel (disabled or verified/failed).
    Returns True if all enabled channels passed, False if any failed.
    Does NOT block startup on failure — the caller decides what to do.
    """
    all_ok = True
    for ch in ALL_CHANNELS:
        if not ch.is_enabled():
            log.info("%-15s: disabled", ch.name)
            continue
        if not ch.verify():
            all_ok = False

    if not all_ok:
        log.warning("One or more notification channels failed verification — "
                    "alerts may not be delivered")
    return all_ok


# ---------------------------------------------------------------------------
# Unified notify — single event
# ---------------------------------------------------------------------------

def notify(event: dict, shutdown=None) -> bool:
    """Send alert to all configured channels. Returns True if all succeeded."""
    app_name = event.get("app_name", event.get("app_domain", "unknown"))
    email = event.get("user_email", "unknown")
    ip = event.get("ip_address", "unknown")
    country = event.get("country", "unknown").upper()
    connection = event.get("connection", "unknown")
    created = format_event_time(event.get("created_at", ""))

    log.info(
        "Blocked login detected:\n"
        "  App      : %s\n"
        "  Email    : %s\n"
        "  IP       : %s\n"
        "  Country  : %s\n"
        "  IdP      : %s\n"
        "  Time     : %s",
        app_name, email, ip, country, connection, created
    )

    results = [ch.send_event(event, shutdown) for ch in get_active_channels()]
    return all(results)


# ---------------------------------------------------------------------------
# Unified notify — burst summary
# ---------------------------------------------------------------------------

def notify_burst(burst: dict, shutdown=None) -> bool:
    """Send a burst summary alert to all configured channels."""
    log.info(
        "Burst alert:\n"
        "  IP       : %s\n"
        "  Attempts : %d in %s\n"
        "  Emails   : %s\n"
        "  Apps     : %s\n"
        "  Countries: %s",
        burst["ip_address"], burst["count"],
        format_duration(burst["window_seconds"]),
        ", ".join(burst["emails"]),
        ", ".join(burst["apps"]),
        ", ".join(burst["countries"]),
    )

    results = [ch.send_burst(burst, shutdown) for ch in get_active_channels()]
    return all(results)


# ---------------------------------------------------------------------------
# Unified notify — daily digest
# ---------------------------------------------------------------------------

def notify_digest(digest: dict, shutdown=None) -> bool:
    """Send daily digest to all configured channels. Returns True if all succeeded."""
    if digest["total_blocked"] == 0:
        log.info("Daily digest: no blocked events — sending quiet summary")
    else:
        log.info(
            "Daily digest: %d blocked events, %d bursts, %d unique IPs",
            digest["total_blocked"], digest["total_bursts"],
            digest["unique_ips"],
        )

    results = [ch.send_digest(digest, shutdown) for ch in get_active_channels()]
    return all(results)