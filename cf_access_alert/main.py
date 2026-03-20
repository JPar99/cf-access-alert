"""Main entrypoint — polling loop with catchup and deduplication."""

import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from . import config
from .banner import print_banner
from .cloudflare import fetch_logs, filter_events
from .config import format_duration
from .notifications import notify
from .shutdown import GracefulShutdown
from .state import load, save
from .timeutil import utc_to_local

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    stream=sys.stdout,
)
log = logging.getLogger("cf-access-alert")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print_banner()
    shutdown = GracefulShutdown()
    config.validate()

    state = load()
    alerted_ids = state["alerted_ids"]
    last_poll = state["last_poll"]

    log.info("Loaded %d previously alerted ray_id(s)", len(alerted_ids))
    if last_poll:
        log.info("Last successful poll: %s", utc_to_local(last_poll))

    first_run = True

    while not shutdown.should_exit:
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Determine how far back to look
        if last_poll:
            last_poll_dt = datetime.strptime(
                last_poll, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            since_dt = last_poll_dt - timedelta(seconds=config.MIN_LOOKBACK)

            earliest_allowed = now - timedelta(seconds=config.MAX_CATCHUP)
            if since_dt < earliest_allowed:
                since_dt = earliest_allowed
                if first_run:
                    log.warning(
                        "Container was down longer than MAX_CATCHUP (%dd). "
                        "Catching up from %s",
                        config.MAX_CATCHUP // 86400,
                        utc_to_local(
                            earliest_allowed.strftime("%Y-%m-%dT%H:%M:%SZ")
                        ),
                    )
        else:
            since_dt = now - timedelta(seconds=config.MIN_LOOKBACK)

        since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        log.info("Polling CF Access logs | checking from %s to %s | next poll in %s",
                 utc_to_local(since_str), utc_to_local(now_str), format_duration(config.POLL_INTERVAL))

        events = fetch_logs(since_str, now_str, shutdown)
        blocked = filter_events(events)

        new_blocked = [
            ev for ev in blocked if ev.get("ray_id") not in alerted_ids
        ]

        if new_blocked:
            log.info(
                "Found %d new blocked event(s) (%d total, %d already alerted)",
                len(new_blocked), len(blocked), len(blocked) - len(new_blocked),
            )
            for ev in new_blocked:
                notify(ev, shutdown)
                alerted_ids.add(ev.get("ray_id"))
        else:
            if blocked:
                log.debug("Found %d blocked event(s) but all already alerted",
                          len(blocked))
            else:
                log.info("No blocked events found")

        last_poll = now_str
        save(alerted_ids, last_poll)
        first_run = False

        # Interruptible sleep
        for _ in range(config.POLL_INTERVAL):
            if shutdown.should_exit:
                break
            time.sleep(1)

    log.info("Saving state before exit")
    save(alerted_ids, last_poll)
    log.info("Shutdown complete")