"""Channel registry — import channels here to register them.

To add a new channel:
1. Create a new file in this directory (e.g. slack.py)
2. Implement a class that extends NotificationChannel
3. Import it below and add it to ALL_CHANNELS
"""

from .pushover import PushoverChannel
from .discord import DiscordChannel
from .ntfy import NtfyChannel

ALL_CHANNELS = [
    PushoverChannel(),
    DiscordChannel(),
    NtfyChannel(),
]


def get_active_channels():
    """Return only channels that are configured (env vars present)."""
    return [ch for ch in ALL_CHANNELS if ch.is_enabled()]
