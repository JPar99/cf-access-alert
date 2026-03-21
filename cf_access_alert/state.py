"""State persistence — track alerted ray_ids, last poll, and digest schedule.

State is written atomically (write-to-temp, then rename) so a crash
mid-write never corrupts the file.  Alerted ray_ids are stored as an
ordered list so trimming always keeps the *most recent* IDs.
"""

import json
import logging
import os
from pathlib import Path

from . import config

log = logging.getLogger("cf-access-alert")


def load() -> dict:
    """Load persisted state: alerted ray_ids, last poll, and next digest time.

    Returns alerted_ids as a list (preserving insertion order) plus a
    companion set for O(1) membership checks.
    """
    try:
        data = json.loads(Path(config.STATE_FILE).read_text())
        id_list = data.get("alerted_ids", [])
        return {
            "alerted_ids": list(id_list),
            "alerted_set": set(id_list),
            "last_poll": data.get("last_poll"),
            "next_digest_at": data.get("next_digest_at"),
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {
            "alerted_ids": [],
            "alerted_set": set(),
            "last_poll": None,
            "next_digest_at": None,
        }


def save(alerted_ids: list, last_poll: str, next_digest_at: str = None) -> None:
    """Save state atomically. Cap ray_ids at 500 (most recent) to prevent unbounded growth."""
    trimmed = alerted_ids[-500:]
    state = {
        "alerted_ids": trimmed,
        "last_poll": last_poll,
    }
    if next_digest_at is not None:
        state["next_digest_at"] = next_digest_at

    state_path = Path(config.STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file then rename (rename is atomic on Linux)
    tmp_path = state_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state))
    os.replace(str(tmp_path), str(state_path))

    log.debug("State saved: %d ray_ids, last_poll=%s, next_digest=%s",
              len(trimmed), last_poll, next_digest_at)