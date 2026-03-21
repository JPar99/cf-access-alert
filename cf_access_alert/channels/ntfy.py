"""ntfy notification channel (ntfy.sh or self-hosted)."""

import logging
import os

from .base import NotificationChannel
from ..config import format_duration
from ..timeutil import format_event_time

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

log = logging.getLogger("cf-access-alert")


class NtfyChannel(NotificationChannel):
    name = "ntfy"

    def __init__(self):
        self.url = os.environ.get("NTFY_URL", "https://ntfy.sh")
        self.topic = os.environ.get("NTFY_TOPIC", "")
        self.token = os.environ.get("NTFY_TOKEN", "")
        self.priority = int(os.environ.get("NTFY_PRIORITY", "4"))

    def is_enabled(self) -> bool:
        return bool(self.topic)

    def _auth_headers(self) -> dict | None:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return None

    def _post_url(self) -> str:
        return self.url.rstrip("/")

    def verify(self) -> bool:
        if not self.is_enabled():
            return True

        url = f"{self._post_url()}/{self.topic}/json?poll=1&since=0"

        req = Request(url, method="GET")
        req.add_header("User-Agent", "cf-access-alert/1.0")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    log.info("ntfy          : verified ✓ (%s)", self.url)
                    return True
                log.warning("ntfy          : returned HTTP %s", resp.status)
                return False
        except HTTPError as exc:
            if exc.code == 401 or exc.code == 403:
                log.warning("ntfy          : auth failed — HTTP %s "
                            "(check NTFY_TOKEN)", exc.code)
            else:
                log.warning("ntfy          : verification failed — HTTP %s", exc.code)
            return False
        except (URLError, OSError) as exc:
            log.warning("ntfy          : unreachable — %s", exc)
            return False

    def send_event(self, event: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        app_name = event.get("app_name", event.get("app_domain", "unknown"))
        email = event.get("user_email", "unknown")
        ip = event.get("ip_address", "unknown")
        country = event.get("country", "unknown").upper()
        connection = event.get("connection", "unknown")
        created = format_event_time(event.get("created_at", ""))

        payload = {
            "topic": self.topic,
            "title": f"CF Access blocked: {app_name}",
            "message": (
                f"App: {app_name}\n"
                f"Email: {email}\n"
                f"IP: {ip}\n"
                f"Country: {country}\n"
                f"IdP: {connection}\n"
                f"Time: {created}"
            ),
            "tags": ["rotating_light", "lock"],
            "priority": self.priority,
        }
        return self.post_json(self._post_url(), payload, shutdown,
                              extra_headers=self._auth_headers())

    def send_burst(self, burst: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        payload = {
            "topic": self.topic,
            "title": f"⚠ Brute-force: {burst['ip_address']}",
            "message": (
                f"IP: {burst['ip_address']}\n"
                f"Blocked attempts: {burst['count']} in {format_duration(burst['window_seconds'])}\n"
                f"Emails: {', '.join(burst['emails'])}\n"
                f"Apps: {', '.join(burst['apps'])}\n"
                f"Countries: {', '.join(burst['countries'])}"
            ),
            "tags": ["skull", "warning"],
            "priority": 5,
        }
        return self.post_json(self._post_url(), payload, shutdown,
                              extra_headers=self._auth_headers())

    def send_digest(self, digest: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        payload = {
            "topic": self.topic,
            "title": "📊 CF Access daily digest",
            "message": self.digest_message(digest),
            "tags": ["bar_chart"],
            "priority": 3,
        }
        return self.post_json(self._post_url(), payload, shutdown,
                              extra_headers=self._auth_headers())
