"""State persistence — track alerted ray_ids and last poll timestamp."""

import json
import logging
from pathlib import Path

from . import config

log = logging.getLogger("cf-access-alert")


def load() -> dict:
    """Load persisted state: alerted ray_ids and last successful poll time."""
    try:
        data = json.loads(Path(config.STATE_FILE).read_text())
        return {
            "alerted_ids": set(data.get("alerted_ids", [])),
            "last_poll": data.get("last_poll"),
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {"alerted_ids": set(), "last_poll": None}


def save(alerted_ids: set, last_poll: str) -> None:
    """Save state. Cap ray_ids at 500 to prevent unbounded growth."""
    trimmed = list(alerted_ids)[-500:]
    Path(config.STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(config.STATE_FILE).write_text(json.dumps({
        "alerted_ids": trimmed,
        "last_poll": last_poll,
    }))
    log.debug("State saved: %d ray_ids, last_poll=%s", len(trimmed), last_poll)
