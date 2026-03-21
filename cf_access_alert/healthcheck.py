#!/usr/bin/env python3
"""Docker HEALTHCHECK script — exits 0 if poller is alive, 1 if stale.

Checks that the state file was updated within POLL_INTERVAL * 3.
Uses a generous multiplier to avoid false positives during catchup
or slow API responses. No HTTP port needed.
"""

import json
import os
import sys
import time
from pathlib import Path

STATE_FILE = "/data/last_seen.json"

# Read POLL_INTERVAL from env (same default as config.py)
poll_raw = os.environ.get("POLL_INTERVAL", "5m").strip().lower()
try:
    if poll_raw.endswith("d"):
        poll_seconds = int(poll_raw[:-1]) * 86400
    elif poll_raw.endswith("h"):
        poll_seconds = int(poll_raw[:-1]) * 3600
    elif poll_raw.endswith("m"):
        poll_seconds = int(poll_raw[:-1]) * 60
    elif poll_raw.endswith("s"):
        poll_seconds = int(poll_raw[:-1])
    else:
        poll_seconds = int(poll_raw)
except (ValueError, IndexError):
    poll_seconds = 300

MAX_AGE = poll_seconds * 3  # generous: 3x poll interval


def main() -> int:
    state_path = Path(STATE_FILE)
    if not state_path.exists():
        # First run — container just started, give it time
        return 0

    try:
        data = json.loads(state_path.read_text())
        last_poll = data.get("last_poll")
        if not last_poll:
            return 0  # no poll yet, still starting up

        # Check file modification time (more reliable than parsing timestamps)
        age = time.time() - state_path.stat().st_mtime
        if age > MAX_AGE:
            print(f"UNHEALTHY: state file is {int(age)}s old (limit: {MAX_AGE}s)")
            return 1

        return 0
    except (json.JSONDecodeError, OSError) as exc:
        print(f"UNHEALTHY: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())