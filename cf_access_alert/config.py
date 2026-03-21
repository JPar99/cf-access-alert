"""
Configuration — load and validate environment variables.

All secrets are read from env vars only. Redaction helpers ensure
no secret value is ever written to stdout/stderr.
"""

import logging
import os
import re
import sys

log = logging.getLogger("cf-access-alert")


# ---------------------------------------------------------------------------
# Duration parser — supports 30s, 10m, 2h, 7d or plain seconds
# ---------------------------------------------------------------------------

def parse_duration(value: str, default: int) -> int:
    """Parse a duration string like '30s', '10m', '2h', '7d' into seconds.
    Plain integers are treated as seconds for backwards compatibility."""
    value = value.strip().lower()
    if not value:
        return default
    match = re.match(r"^(\d+)\s*(s|m|h|d)?$", value)
    if not match:
        log.warning("Invalid duration '%s', using default %ds", value, default)
        return default
    num = int(match.group(1))
    unit = match.group(2) or "s"
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return num * multipliers[unit]


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable string like '5m', '2h', '7d'."""
    if seconds >= 86400 and seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


# ---------------------------------------------------------------------------
# Cloudflare
# ---------------------------------------------------------------------------
CF_API_TOKEN: str = os.environ.get("CF_API_TOKEN", "")
CF_ACCOUNT_ID: str = os.environ.get("CF_ACCOUNT_ID", "")
# Comma-separated list of app UIDs to monitor (empty = all apps)
CF_APP_UIDS: set = set(
    u.strip() for u in os.environ.get("CF_APP_UIDS", "").split(",") if u.strip()
)
CF_PAGE_SIZE: int = 100

# ---------------------------------------------------------------------------
# Notifications — channel-specific config lives in channels/*.py
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Burst detection
# ---------------------------------------------------------------------------
BURST_THRESHOLD: int = int(os.environ.get("BURST_THRESHOLD", "5"))
BURST_WINDOW: int = parse_duration(os.environ.get("BURST_WINDOW", "5m"), 300)

# ---------------------------------------------------------------------------
# Daily digest
# ---------------------------------------------------------------------------
DIGEST_ENABLED: bool = os.environ.get("DIGEST_ENABLED", "true").lower() in ("true", "1", "yes")
_digest_time_raw: str = os.environ.get("DIGEST_TIME", "08:00")
try:
    _dt_parts = _digest_time_raw.strip().split(":")
    DIGEST_HOUR: int = int(_dt_parts[0])
    DIGEST_MINUTE: int = int(_dt_parts[1]) if len(_dt_parts) > 1 else 0
except (ValueError, IndexError):
    DIGEST_HOUR: int = 8
    DIGEST_MINUTE: int = 0

# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------
NOTIFY_RETRIES: int = int(os.environ.get("NOTIFY_RETRIES", "3"))
NOTIFY_RETRY_DELAY: int = parse_duration(os.environ.get("NOTIFY_RETRY_DELAY", "10s"), 10)

# ---------------------------------------------------------------------------
# State, catchup, and polling
# ---------------------------------------------------------------------------
POLL_INTERVAL: int = parse_duration(os.environ.get("POLL_INTERVAL", "5m"), 300)
STATE_FILE: str = "/data/last_seen.json"
MIN_LOOKBACK: int = parse_duration(os.environ.get("LOOKBACK_BUFFER", "10m"), 600)
MAX_CATCHUP: int = parse_duration(os.environ.get("MAX_CATCHUP", "7d"), 604800)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Update checker
# ---------------------------------------------------------------------------
UPDATE_CHECK: bool = os.environ.get("UPDATE_CHECK", "true").lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Redaction helpers
# ---------------------------------------------------------------------------

def redact(value: str) -> str:
    """Return a redacted representation safe for logs."""
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...***"


def redact_url(url: str) -> str:
    """Redact account IDs and webhook tokens from URLs."""
    url = re.sub(r"/accounts/[a-f0-9]+/", "/accounts/REDACTED/", url)
    url = re.sub(r"(/webhooks/\d+/)[\w\-]+", r"\1REDACTED", url)
    return url


def redact_payload(payload: dict, service_name: str) -> dict:
    """Return a copy of payload with secret fields redacted."""
    safe = dict(payload)
    if service_name == "Pushover":
        if "token" in safe:
            safe["token"] = redact(safe["token"])
        if "user" in safe:
            safe["user"] = redact(safe["user"])
    return safe


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate() -> None:
    """Validate required config and log startup summary."""
    from .channels import ALL_CHANNELS

    missing = []
    if not CF_API_TOKEN:
        missing.append("CF_API_TOKEN")
    if not CF_ACCOUNT_ID:
        missing.append("CF_ACCOUNT_ID")

    active = [ch for ch in ALL_CHANNELS if ch.is_enabled()]
    if not active:
        names = ", ".join(ch.name for ch in ALL_CHANNELS)
        missing.append(f"At least one notification channel must be configured ({names})")

    if missing:
        log.error("Missing required configuration: %s", ", ".join(missing))
        sys.exit(1)

    log.info("Log level      : %s", LOG_LEVEL)
    log.info("CF_ACCOUNT_ID  : %s", redact(CF_ACCOUNT_ID))
    log.info("CF_APP_UIDS    : %s",
             ", ".join(sorted(CF_APP_UIDS)) if CF_APP_UIDS else "(all apps)")
    for ch in ALL_CHANNELS:
        status = "enabled" if ch.is_enabled() else "disabled"
        log.info("%-15s: %s", ch.name, status)
    log.info("Burst detect   : threshold=%d in %s window",
             BURST_THRESHOLD, format_duration(BURST_WINDOW))
    log.info("Daily digest   : %s (at %02d:%02d local)",
             "enabled" if DIGEST_ENABLED else "disabled", DIGEST_HOUR, DIGEST_MINUTE)
    log.info("Poll interval  : %s", format_duration(POLL_INTERVAL))
    log.info("Lookback buffer: %s", format_duration(MIN_LOOKBACK))
    log.info("Notify retries : %d (delay %s)", NOTIFY_RETRIES, format_duration(NOTIFY_RETRY_DELAY))
    log.info("Max catchup    : %s", format_duration(MAX_CATCHUP))
