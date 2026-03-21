"""Base notification channel — shared retry logic and digest helpers."""

import json
import logging
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .. import config
from ..banner import VERSION
from ..config import redact_url, redact_payload

log = logging.getLogger("cf-access-alert")

USER_AGENT = f"cf-access-alert/{VERSION}"


class NotificationChannel:
    """Abstract base for notification channels.

    Subclasses must set ``name`` and implement:
    - ``is_enabled()``
    - ``verify()``
    - ``send_event(event, shutdown)``
    - ``send_burst(burst, shutdown)``
    - ``send_digest(digest, shutdown)``
    """

    name: str = "unknown"

    # ------------------------------------------------------------------
    # Interface (override in subclasses)
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return True when the channel is configured (env vars present)."""
        raise NotImplementedError

    def verify(self) -> bool:
        """Startup check — verify credentials / connectivity."""
        raise NotImplementedError

    def send_event(self, event: dict, shutdown=None) -> bool:
        """Send a single blocked-login alert. Return True on success."""
        raise NotImplementedError

    def send_burst(self, burst: dict, shutdown=None) -> bool:
        """Send a burst / brute-force summary. Return True on success."""
        raise NotImplementedError

    def send_digest(self, digest: dict, shutdown=None) -> bool:
        """Send a daily digest summary. Return True on success."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def post_json(self, url: str, payload: dict, shutdown=None,
                  extra_headers: dict | None = None) -> bool:
        """POST JSON with retry + exponential backoff. Returns True on success."""
        data = json.dumps(payload).encode()

        for attempt in range(1, config.NOTIFY_RETRIES + 1):
            if shutdown and shutdown.should_exit:
                log.info("%s skipped — shutting down", self.name)
                return False

            log.debug("%s POST to: %s (attempt %d/%d)",
                      self.name, redact_url(url), attempt, config.NOTIFY_RETRIES)
            if attempt == 1:
                log.debug("%s payload: %s",
                          self.name, json.dumps(redact_payload(payload, self.name)))

            req = Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", USER_AGENT)
            if extra_headers:
                for key, value in extra_headers.items():
                    req.add_header(key, value)

            try:
                with urlopen(req, timeout=15) as resp:
                    if resp.status < 300:
                        log.info("%s success: HTTP %s", self.name, resp.status)
                        return True
                    log.warning("%s returned HTTP %s", self.name, resp.status)
            except HTTPError as exc:
                log.warning("%s HTTP error %s (attempt %d/%d)",
                            self.name, exc.code, attempt, config.NOTIFY_RETRIES)
            except Exception:
                log.exception("%s request failed (attempt %d/%d)",
                              self.name, attempt, config.NOTIFY_RETRIES)

            if attempt < config.NOTIFY_RETRIES:
                delay = min(config.NOTIFY_RETRY_DELAY * (2 ** (attempt - 1)), 60)
                log.info("%s retrying in %ds", self.name, delay)
                for _ in range(delay):
                    if shutdown and shutdown.should_exit:
                        log.info("%s retry aborted — shutting down", self.name)
                        return False
                    time.sleep(1)

        log.error("%s failed after %d attempts", self.name, config.NOTIFY_RETRIES)
        return False

    # ------------------------------------------------------------------
    # Digest text helpers (reusable by plain-text channels)
    # ------------------------------------------------------------------

    @staticmethod
    def format_top_list(items: list[tuple[str, int]], label: str) -> str:
        """Format a list of (name, count) tuples into a readable string."""
        if not items:
            return f"  {label}: (none)"
        lines = [f"  {label}:"]
        for name, count in items:
            lines.append(f"    {name}: {count}")
        return "\n".join(lines)

    @staticmethod
    def digest_message(digest: dict) -> str:
        """Build the plain-text digest message body."""
        fmt = NotificationChannel.format_top_list
        lines = [
            "Daily summary:",
            f"  Total blocked: {digest['total_blocked']}",
            f"  Burst alerts: {digest['total_bursts']}",
            f"  Unique IPs: {digest['unique_ips']}",
            f"  Unique emails: {digest['unique_emails']}",
            "",
            fmt(digest["top_ips"], "Top IPs"),
            fmt(digest["top_emails"], "Top emails"),
            fmt(digest["top_apps"], "Top apps"),
            fmt(digest["top_countries"], "Top countries"),
        ]
        return "\n".join(lines)