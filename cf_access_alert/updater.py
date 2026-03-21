"""Update checker — compare running version against latest GitHub release."""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .banner import VERSION

log = logging.getLogger("cf-access-alert")

GITHUB_REPO = "JPar99/cf-access-alert"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(version_str: str) -> tuple:
    """Parse a version string like '1.1.0' into a comparable tuple (1, 1, 0)."""
    try:
        clean = version_str.lstrip("v")
        return tuple(int(x) for x in clean.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_for_updates() -> None:
    """Check GitHub for a newer release and log a message if one is found."""
    from . import config
    if not config.UPDATE_CHECK:
        log.debug("Update check disabled via UPDATE_CHECK=false")
        return

    log.debug("Checking for updates at %s", GITHUB_API_URL)

    req = Request(GITHUB_API_URL, method="GET")
    req.add_header("User-Agent", f"cf-access-alert/{VERSION}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as exc:
        log.debug("Update check failed: HTTP %s", exc.code)
        return
    except URLError as exc:
        log.debug("Update check failed: %s", exc.reason)
        return
    except Exception:
        log.debug("Update check failed unexpectedly")
        return

    latest_tag = data.get("tag_name", "")
    latest_name = data.get("name", latest_tag)
    published_at = data.get("published_at", "")
    html_url = data.get("html_url", "")

    current_version = _parse_version(VERSION)
    latest_version = _parse_version(latest_tag)

    if latest_version > current_version:
        # Calculate how old the release is
        age = _format_age(published_at)
        log.warning(
            "A new release is available: %s (released %s)\n"
            "  You are running: v%s\n"
            "  Update: %s",
            latest_name, age, VERSION, html_url
        )
    elif latest_version == current_version:
        log.info("You are running the latest release: v%s", VERSION)
    else:
        log.info(
            "You are running v%s (ahead of latest release %s)",
            VERSION, latest_tag
        )


def _format_age(published_at: str) -> str:
    """Format a GitHub published_at timestamp into a human-readable age."""
    from datetime import datetime, timezone

    if not published_at:
        return "unknown date"

    try:
        # GitHub format: 2026-03-20T16:35:05Z
        pub_dt = datetime.strptime(
            published_at, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - pub_dt

        days = delta.days
        if days == 0:
            return "today"
        elif days == 1:
            return "1 day ago"
        elif days < 30:
            return f"{days} days ago"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    except (ValueError, TypeError):
        return "unknown date"