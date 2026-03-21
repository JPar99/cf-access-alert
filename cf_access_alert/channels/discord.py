"""Discord webhook notification channel."""

import logging
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .base import NotificationChannel
from ..config import format_duration
from ..timeutil import format_event_time

log = logging.getLogger("cf-access-alert")


class DiscordChannel(NotificationChannel):
    name = "Discord"

    def __init__(self):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")

    def is_enabled(self) -> bool:
        return bool(self.webhook_url)

    def verify(self) -> bool:
        if not self.is_enabled():
            return True

        req = Request(self.webhook_url, method="GET")
        req.add_header("User-Agent", "cf-access-alert/1.0")

        try:
            with urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                channel = body.get("name", "unknown")
                log.info("Discord       : verified ✓ (webhook: %s)", channel)
                return True
        except HTTPError as exc:
            log.warning("Discord       : verification failed — HTTP %s "
                        "(check DISCORD_WEBHOOK_URL)", exc.code)
            return False
        except (URLError, OSError) as exc:
            log.warning("Discord       : unreachable — %s", exc)
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
        return self.post_json(self.webhook_url, payload, shutdown)

    def send_burst(self, burst: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        payload = {
            "username": "CF Access Alert",
            "embeds": [
                {
                    "title": f"⚠ Brute-force detected — {burst['ip_address']}",
                    "color": 0xFF0000,
                    "fields": [
                        {"name": "IP Address", "value": burst["ip_address"], "inline": True},
                        {"name": "Blocked Attempts",
                         "value": f"{burst['count']} in {format_duration(burst['window_seconds'])}",
                         "inline": True},
                        {"name": "Emails", "value": ", ".join(burst["emails"]), "inline": False},
                        {"name": "Applications", "value": ", ".join(burst["apps"]), "inline": False},
                        {"name": "Countries", "value": ", ".join(burst["countries"]), "inline": True},
                    ],
                }
            ],
        }
        return self.post_json(self.webhook_url, payload, shutdown)

    def send_digest(self, digest: dict, shutdown=None) -> bool:
        if not self.is_enabled():
            return True

        def _top_field(items: list[tuple[str, int]]) -> str:
            if not items:
                return "(none)"
            return "\n".join(f"`{name}`: {count}" for name, count in items)

        payload = {
            "username": "CF Access Alert",
            "embeds": [
                {
                    "title": "📊 Daily digest",
                    "color": 0x3498DB,
                    "fields": [
                        {"name": "Total Blocked", "value": str(digest["total_blocked"]), "inline": True},
                        {"name": "Burst Alerts", "value": str(digest["total_bursts"]), "inline": True},
                        {"name": "Unique IPs", "value": str(digest["unique_ips"]), "inline": True},
                        {"name": "Top IPs", "value": _top_field(digest["top_ips"]), "inline": False},
                        {"name": "Top Emails", "value": _top_field(digest["top_emails"]), "inline": False},
                        {"name": "Top Apps", "value": _top_field(digest["top_apps"]), "inline": True},
                        {"name": "Top Countries", "value": _top_field(digest["top_countries"]), "inline": True},
                    ],
                }
            ],
        }
        return self.post_json(self.webhook_url, payload, shutdown)
