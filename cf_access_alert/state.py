"""State persistence — track alerted ray_ids, last poll, and digest schedule."""

import json
import logging
from pathlib import Path

from . import config

log = logging.getLogger("cf-access-alert")


def load() -> dict:
    """Load persisted state: alerted ray_ids, last poll, and next digest time."""
    try:
        data = json.loads(Path(config.STATE_FILE).read_text())
        return {
            "alerted_ids": set(data.get("alerted_ids", [])),
            "last_poll": data.get("last_poll"),
            "next_digest_at": data.get("next_digest_at"),
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {"alerted_ids": set(), "last_poll": None, "next_digest_at": None}


def save(alerted_ids: set, last_poll: str, next_digest_at: str = None) -> None:
    """Save state. Cap ray_ids at 500 to prevent unbounded growth."""
    trimmed = list(alerted_ids)[-500:]
    state = {
        "alerted_ids": trimmed,
        "last_poll": last_poll,
    }
    if next_digest_at is not None:
        state["next_digest_at"] = next_digest_at
    Path(config.STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(config.STATE_FILE).write_text(json.dumps(state))
    log.debug("State saved: %d ray_ids, last_poll=%s, next_digest=%s",
              len(trimmed), last_poll, next_digest_at)