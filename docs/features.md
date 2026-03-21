# Features

## Burst Detection

When someone brute-forces your apps, you don't want 50 individual notifications. Burst detection groups rapid blocked attempts from the same IP into a single alert.

### How it works

- The tracker maintains an in-memory sliding window of blocked events per IP address
- Each poll cycle, new blocked events are classified as either individual alerts or part of a burst
- If an IP has ≥ `BURST_THRESHOLD` (default 5) blocked attempts within `BURST_WINDOW` (default 5m), a single "brute-force detected" summary is sent instead of individual alerts
- The tracker resets on container restart (intentional — avoids stale state issues)

### Configuration

```
BURST_THRESHOLD=5    # blocks from same IP to trigger burst mode
BURST_WINDOW=5m      # sliding window
```

## Daily Digest

A periodic summary of all blocked events, sent to all configured notification channels.

### How it works

- An in-memory accumulator collects stats (emails, IPs, apps, countries) from each poll cycle
- At `DIGEST_TIME`, the accumulated stats are formatted and sent to all channels
- The accumulator resets after each digest is sent
- The schedule (`next_digest_at`) is persisted in the state file so it survives restarts
- The schedule is recalculated on every startup, so changing `DIGEST_TIME` takes effect immediately
- If no events occurred during the period, a quiet "no blocked events" summary is still sent — so you know the monitor is alive

### Configuration

```
DIGEST_ENABLED=true    # enable/disable
DIGEST_TIME=08:00      # local time (HH:MM)
```

### Note on restarts

The accumulator is in-memory only. If the container restarts at 14:00 and the digest fires at 08:00 the next day, the digest covers 14:00–08:00 (18 hours), not a full 24 hours. This is by design to keep things simple and avoid complex state management.

## Downtime Recovery

On restart, the container reads the last poll timestamp from persistent state and catches up on missed events.

- If the container was down for 3 hours, it queries the last 3 hours plus the lookback buffer
- If it was down for 3 days, it queries the last 3 days
- `MAX_CATCHUP` (default 7 days) caps how far back it will look to prevent extremely large API queries
- All caught-up events go through the same deduplication and burst detection pipeline

## Docker HEALTHCHECK

The container includes a Docker HEALTHCHECK that reports healthy/unhealthy status without opening any network port.

### How it works

- Docker runs a Python script inside the container every 60 seconds
- The script checks if the state file (`/data/last_seen.json`) was modified within `POLL_INTERVAL × 3`
- A generous 3× multiplier avoids false positives during catchup or slow API responses
- `start-period=120s` gives the container time to complete its first poll before health checks begin

### Checking status

```bash
docker inspect --format='{{.State.Health.Status}}' cf-access-alert
```

Returns `healthy`, `unhealthy`, or `starting`.

## Deduplication

Every blocked event from the Cloudflare API has a unique `ray_id`. The container tracks which ray_ids have already been alerted and skips duplicates. The state file stores up to 500 ray_ids to prevent unbounded growth.

## Automatic Pagination

The Cloudflare API returns up to 100 events per page. If there are more, the container automatically paginates through all pages (up to 5,000 events per poll cycle).
