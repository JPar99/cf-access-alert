"""Main entrypoint — polling loop with catchup, deduplication, burst detection, and daily digest."""

import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from . import config
from .banner import print_banner
from .burst import BurstTracker
from .cloudflare import fetch_logs, filter_events
from .config import format_duration
from .digest import DigestAccumulator, compute_next_digest, is_digest_due
from .notifications import notify, notify_burst, notify_digest
from .shutdown import GracefulShutdown
from .state import load, save
from .timeutil import utc_to_local
from .updater import check_for_updates

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
    check_for_updates()

    state = load()
    alerted_ids = state["alerted_ids"]      # ordered list (for trimming)
    alerted_set = state["alerted_set"]      # set (for O(1) lookups)
    last_poll = state["last_poll"]
    next_digest_at = state.get("next_digest_at")

    log.info("Loaded %d previously alerted ray_id(s)", len(alerted_ids))
    if last_poll:
        log.info("Last successful poll: %s", utc_to_local(last_poll))

    burst_tracker = BurstTracker()
    digest = DigestAccumulator()

    # Always (re)calculate digest schedule on startup so DIGEST_TIME changes take effect
    if config.DIGEST_ENABLED:
        now = datetime.now(timezone.utc)
        local_now = now.astimezone()
        next_dt = compute_next_digest(local_now)
        next_digest_at = next_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log.info("Digest scheduled: next at %s", utc_to_local(next_digest_at))

    first_run = True

    while not shutdown.should_exit:
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # --- Check if digest is due ---
        if config.DIGEST_ENABLED and is_digest_due(next_digest_at):
            summary = digest.build_summary()
            notify_digest(summary, shutdown)
            digest.reset()

            # Schedule next digest
            local_now = now.astimezone()
            next_dt = compute_next_digest(local_now)
            next_digest_at = next_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            log.info("Next digest scheduled: %s", utc_to_local(next_digest_at))
            save(alerted_ids, last_poll, next_digest_at)

        # --- Determine how far back to look ---
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
            ev for ev in blocked if ev.get("ray_id") not in alerted_set
        ]

        if new_blocked:
            log.info(
                "Found %d new blocked event(s) (%d total, %d already alerted)",
                len(new_blocked), len(blocked), len(blocked) - len(new_blocked),
            )

            # Run burst detection on the new batch
            individual, bursts = burst_tracker.classify(new_blocked)

            # Send individual alerts and feed digest
            for ev in individual:
                notify(ev, shutdown)
                ray_id = ev.get("ray_id")
                alerted_ids.append(ray_id)
                alerted_set.add(ray_id)
                digest.record_event(ev)

            # Send burst summaries and feed digest
            for burst in bursts:
                notify_burst(burst, shutdown)
                digest.record_burst(burst)

            # Mark all new events as alerted (burst or not)
            for ev in new_blocked:
                ray_id = ev.get("ray_id")
                if ray_id not in alerted_set:
                    alerted_ids.append(ray_id)
                    alerted_set.add(ray_id)
        else:
            if blocked:
                log.debug("Found %d blocked event(s) but all already alerted",
                          len(blocked))
            else:
                log.info("No blocked events found")

        last_poll = now_str
        save(alerted_ids, last_poll, next_digest_at)
        first_run = False

        # Interruptible sleep
        for _ in range(config.POLL_INTERVAL):
            if shutdown.should_exit:
                break
            time.sleep(1)

    log.info("Saving state before exit")
    save(alerted_ids, last_poll, next_digest_at)
    log.info("Shutdown complete")