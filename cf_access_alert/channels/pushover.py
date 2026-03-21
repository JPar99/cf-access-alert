"""Pushover notification channel."""

import json
import logging
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .base import NotificationChannel
from ..config import format_duration, redact
from ..timeutil import format_event_time

log = logging.getLogger("cf-access-alert")

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_VALIDATE_URL = "https://api.pushover.net/1/users/validate.json"


class PushoverChannel(NotificationChannel):
    name = "Pushover"

    def __init__(self):
        self.user_key = os.environ.get("PUSHOVER_USER_KEY", "")
        self.app_token = os.environ.get("PUSHOVER_APP_TOKEN", "")
        self.priority = os.environ.get("PUSHOVER_PRIORITY", "0")
        self.sound = os.environ.get("PUSHOVER_SOUND", "pushover")

    def is_enabled(self) -> bool:
        return bool(self.user_key)

    def verify(self) -> bool:
        if not self.is_enabled():
            return True

        payload = {"token": self.app_token, "user": self.user_key}
        data = json.dumps(payload).encode()

        req = Request(PUSHOVER_VALIDATE_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "cf-access-alert/1.0")

        try:
            with urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                if body.get("status") == 1:
                    log.info("Pushover      : verified ✓")
                    return True
                log.warning("Pushover      : validation failed — %s",
                            ", ".join(body.get("errors", ["unknown error"])))
                return False
        except HTTPError as exc:
            log.warning("Pushover      : validation failed — HTTP %s "
                        "(check PUSHOVER_APP_TOKEN and PUSHOVER_USER_KEY)", exc.code)
            return False
        except (URLError, OSError) as exc:
            log.warning("Pushover      : unreachable — %s", exc)
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
            "token": self.app_token,
            "user": self.user_key,
            "title": f"CF Access blocked: {app_name}",
            "message": (
                f"App: {app_name}\n"
                f"Email: {email}\n"
                f"IP: {ip}\n"
                f"Country: {country}\n"
                f"IdP: {connection}\n"
                f"Time: {created}"
            ),
            "priority": str(self.priority),
            "sound": self.sound,
        }
        return self.post_json(PUSHOVER_API_URL, payload, shutdown)

    def send_burst(self, burst: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        payload = {
            "token": self.app_token,
            "user": self.user_key,
            "title": f"⚠ Brute-force: {burst['ip_address']}",
            "message": (
                f"IP: {burst['ip_address']}\n"
                f"Blocked attempts: {burst['count']} in {format_duration(burst['window_seconds'])}\n"
                f"Emails: {', '.join(burst['emails'])}\n"
                f"Apps: {', '.join(burst['apps'])}\n"
                f"Countries: {', '.join(burst['countries'])}"
            ),
            "priority": "1",
            "sound": self.sound,
        }
        return self.post_json(PUSHOVER_API_URL, payload, shutdown)

    def send_digest(self, digest: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        payload = {
            "token": self.app_token,
            "user": self.user_key,
            "title": "📊 CF Access daily digest",
            "message": self.digest_message(digest),
            "priority": "-1",
            "sound": self.sound,
        }
        return self.post_json(PUSHOVER_API_URL, payload, shutdown)
