"""Notification senders — Discord, Pushover, with retry and exponential backoff."""

import json
import logging
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from . import config
from .config import redact_url, redact_payload
from .timeutil import format_event_time

log = logging.getLogger("cf-access-alert")


# ---------------------------------------------------------------------------
# Generic POST with retry
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, service_name: str,
               shutdown=None) -> bool:
    """POST JSON to a URL with retry. Returns True on success."""
    data = json.dumps(payload).encode()

    for attempt in range(1, config.NOTIFY_RETRIES + 1):
        if shutdown and shutdown.should_exit:
            log.info("%s skipped — shutting down", service_name)
            return False

        log.debug("%s POST to: %s (attempt %d/%d)",
                  service_name, redact_url(url), attempt, config.NOTIFY_RETRIES)
        if attempt == 1:
            log.debug("%s payload: %s",
                      service_name, json.dumps(redact_payload(payload, service_name)))

        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "cf-access-alert/1.0")

        try:
            with urlopen(req, timeout=15) as resp:
                if resp.status < 300:
                    log.info("%s success: HTTP %s", service_name, resp.status)
                    return True
                log.warning("%s returned HTTP %s", service_name, resp.status)
        except HTTPError as exc:
            log.warning("%s HTTP error %s (attempt %d/%d)",
                        service_name, exc.code, attempt, config.NOTIFY_RETRIES)
        except Exception:
            log.exception("%s request failed (attempt %d/%d)",
                          service_name, attempt, config.NOTIFY_RETRIES)

        if attempt < config.NOTIFY_RETRIES:
            delay = config.NOTIFY_RETRY_DELAY * (2 ** (attempt - 1))
            log.info("%s retrying in %ds", service_name, delay)
            time.sleep(delay)

    log.error("%s failed after %d attempts", service_name, config.NOTIFY_RETRIES)
    return False


# ---------------------------------------------------------------------------
# Pushover
# ---------------------------------------------------------------------------

def send_pushover(event: dict, shutdown=None) -> bool:
    """Send a Pushover notification. Returns True on success."""
    if not config.PUSHOVER_USER_KEY:
        return True

    app_name = event.get("app_name", event.get("app_domain", "unknown"))
    email = event.get("user_email", "unknown")
    ip = event.get("ip_address", "unknown")
    country = event.get("country", "unknown").upper()
    connection = event.get("connection", "unknown")
    created = format_event_time(event.get("created_at", ""))

    payload = {
        "token": config.PUSHOVER_APP_TOKEN,
        "user": config.PUSHOVER_USER_KEY,
        "title": f"CF Access blocked: {app_name}",
        "message": (
            f"App: {app_name}\n"
            f"Email: {email}\n"
            f"IP: {ip}\n"
            f"Country: {country}\n"
            f"IdP: {connection}\n"
            f"Time: {created}"
        ),
        "priority": str(config.PUSHOVER_PRIORITY),
        "sound": config.PUSHOVER_SOUND,
    }
    return _post_json(
        "https://api.pushover.net/1/messages.json", payload, "Pushover", shutdown
    )


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def send_discord(event: dict, shutdown=None) -> bool:
    """Send a Discord webhook notification. Returns True on success."""
    if not config.DISCORD_WEBHOOK_URL:
        return True

    app_name = event.get("app_name", event.get("app_domain", "unknown"))
    email = event.get("user_email", "unknown")
    ip = event.get("ip_address", "unknown")
    country = event.get("country", "unknown").upper()
    connection = event.get("connection", "unknown")
    created = format_event_time(event.get("created_at", ""))
    allowed = event.get("allowed", False)

    color = 0xFF0000 if not allowed else 0xFFA500

    payload = {
        "username": "CF Access Alert",
        "embeds": [
            {
                "title": f"Blocked login — {app_name}",
                "color": color,
                "fields": [
                    {"name": "Application", "value": app_name, "inline": True},
                    {"name": "Email", "value": email, "inline": True},
                    {"name": "IP Address", "value": ip, "inline": True},
                    {"name": "Country", "value": country, "inline": True},
                    {"name": "Identity Provider", "value": connection, "inline": True},
                    {"name": "Time", "value": created, "inline": False},
                ],
            }
        ],
    }
    return _post_json(config.DISCORD_WEBHOOK_URL, payload, "Discord", shutdown)


# ---------------------------------------------------------------------------
# Unified notify
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

    pushover_ok = send_pushover(event, shutdown)
    discord_ok = send_discord(event, shutdown)
    return pushover_ok and discord_ok