# cf-access-alert

Lightweight Docker container that monitors [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/) authentication logs and sends real-time alerts when login attempts are blocked or denied.

Built for homelabs and self-hosters who protect applications (Immich, Jellyfin, etc.) behind Cloudflare Access and want instant notifications when unauthorized users try to log in.

## Features

- **Polls Cloudflare Access authentication logs** via the official API
- **Alerts via Discord webhooks and/or Pushover** with rich formatting
- **Automatic pagination** — handles large result sets (up to 5,000 events per poll)
- **Deduplication** — tracks alerted events by `ray_id` to prevent duplicates
- **Downtime catchup** — on restart, catches up on all missed events (configurable up to 7 days)
- **Retry with exponential backoff** — notifications retry on failure (3 attempts by default)
- **Graceful shutdown** — saves state on SIGTERM/SIGINT before exiting
- **Security-first design** — secrets never appear in logs, non-root container, read-only filesystem
- **Zero external dependencies** — Python stdlib only, ~10 MB image
- **Multi-app support** — monitor one, many, or all Access applications
- **Local timezone support** — logs and notifications display your local time

## Quick Start

### Option 1: Pull from GHCR (recommended)

```bash
mkdir cf-access-alert && cd cf-access-alert
# Download docker-compose.yml and .env.example from this repo
curl -LO https://raw.githubusercontent.com/JPar99/cf-access-alert/main/docker-compose.yml
curl -LO https://raw.githubusercontent.com/JPar99/cf-access-alert/main/.env.example
cp .env.example .env
chmod 600 .env
nano .env
docker compose up -d
```

### Option 2: Build locally

```bash
git clone https://github.com/JPar99/cf-access-alert.git
cd cf-access-alert
cp .env.example .env
chmod 600 .env
nano .env
docker compose up -d --build
```

## Configuration

All configuration is done through environment variables in the `.env` file.

### Required

| Variable | Description |
|---|---|
| `CF_API_TOKEN` | Cloudflare API token with **Account > Access: Audit Logs > Read** permission |
| `CF_ACCOUNT_ID` | Your Cloudflare account ID (found on domain Overview page) |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL (required if Pushover is not configured) |
| `PUSHOVER_USER_KEY` | Pushover user key (required if Discord is not configured) |
| `PUSHOVER_APP_TOKEN` | Pushover application API token (required when using Pushover) |

At least one notification channel (Discord or Pushover) must be configured.

### Optional

| Variable | Default | Description |
|---|---|---|
| `CF_APP_UIDS` | *(empty — all apps)* | Comma-separated Access application UUIDs to monitor |
| `PUSHOVER_PRIORITY` | `0` | Pushover priority: `-1` (silent), `0` (normal), `1` (high) |
| `PUSHOVER_SOUND` | `pushover` | Pushover notification sound |
| `POLL_INTERVAL` | `5m` | How often to poll CF Access logs |
| `LOOKBACK_BUFFER` | `10m` | How far back to look each poll (accounts for CF log delay) |
| `MAX_CATCHUP` | `7d` | Max catchup window after container downtime |
| `NOTIFY_RETRIES` | `3` | Number of retry attempts per notification |
| `NOTIFY_RETRY_DELAY` | `10s` | Base delay between retries (doubles each attempt) |
| `TZ` | `UTC` | Timezone for logs and notifications (e.g. `Europe/Amsterdam`) |
| `LOG_LEVEL` | `INFO` | Log level: `INFO` or `DEBUG` |

Duration values support: `30s` (seconds), `10m` (minutes), `2h` (hours), `7d` (days). Plain numbers are treated as seconds for backwards compatibility.

### Creating a Cloudflare API Token

1. Go to [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **Create Token** > **Create Custom Token**
3. Set permissions: **Account > Access: Audit Logs > Read**
4. Restrict to your specific account under Account Resources
5. Create and copy the token (shown only once)

### Filtering by Application

Cloudflare Access apps have two identifiers in the API:

- **`app_domain`** — for SaaS-type apps this is your `.cloudflareaccess.com` domain, *not* the actual app hostname
- **`app_uid`** — the UUID assigned by Cloudflare (more reliable)

To find your app's UID, query the API:

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/access/logs/access_requests?limit=1" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool
```

To monitor multiple apps, comma-separate the UIDs:

```
CF_APP_UIDS=uid-one-here,uid-two-here,uid-three-here
```

## How It Works

```
┌──────────────────┐    poll every N sec    ┌──────────────────┐
│                  │ ─────────────────────> │                  │
│  cf-access-alert │                        │  Cloudflare API  │
│                  │ <───────────────────── │  Access Logs     │
└────────┬─────────┘    blocked events      └──────────────────┘
         │
         │  deduplicate by ray_id
         │
         ├──────────────> Discord webhook
         │
         └──────────────> Pushover API
```

1. Every `POLL_INTERVAL` seconds, queries the CF Access authentication logs API
2. Looks back from `last_poll - LOOKBACK_BUFFER` to catch delayed log entries
3. Filters for blocked events (`allowed: false`)
4. Optionally filters by app UID
5. Deduplicates against previously alerted `ray_id` values
6. Sends notifications with retry and exponential backoff
7. Persists state (alerted ray_ids + last poll timestamp) to survive restarts

### Downtime Recovery

On restart, the container reads the last poll timestamp from persistent state. If it was down for 3 hours, it queries the last 3 hours + buffer. If it was down for 3 days, it queries the last 3 days. The `MAX_CATCHUP` setting caps this at 7 days by default to prevent extremely large queries.

## Security

This container is designed with security as the top priority:

- **Secrets from `.env` only** — never from CLI args, config files, or labels
- **No secret leakage in logs** — all sensitive values are redacted in every log line, including debug mode
- **Non-root execution** — runs as `appuser` inside the container
- **Read-only filesystem** — `read_only: true` with minimal tmpfs
- **No privileges** — `no-new-privileges` security option
- **No exposed ports** — outbound-only HTTP requests
- **No Docker socket** — no access to the host Docker daemon
- **Resource limits** — capped at 64 MB RAM and 0.25 CPU
- **Zero dependencies** — Python stdlib only, minimal attack surface
- **`.dockerignore`** — secrets excluded from build context
- **`.gitignore`** — `.env` excluded from version control

## Docker Compose

```yaml
services:
  cf-access-alert:
    container_name: cf-access-alert
    image: ghcr.io/JPar99/cf-access-alert:latest
    # Uncomment to build locally instead:
    # build: .
    restart: unless-stopped
    volumes:
      - cf-access-alert-data:/data
    env_file:
      - .env
    environment:
      - TZ=${TZ:-Europe/Amsterdam}
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=10m
    mem_limit: 64m
    cpus: 0.25

volumes:
  cf-access-alert-data:
```

## Commands

```bash
# Build and start
docker compose up -d --build

# View logs
docker logs -f cf-access-alert

# Restart after .env changes
docker compose restart

# Rebuild after script changes
docker compose up -d --build

# Reset state (will re-alert on recent events)
docker compose down
docker volume rm cf-access-alert_cf-access-alert-data
docker compose up -d --build

# Graceful stop (saves state)
docker compose down
```

## Example Output

### Container Logs (INFO)

```
2026-03-20T18:23:36+0100 [INFO] Polling CF Access logs: 2026-03-20 18:13:36 CET -> 2026-03-20 18:23:36 CET
2026-03-20T18:23:37+0100 [INFO] Found 1 new blocked event(s) (1 total, 0 already alerted)
2026-03-20T18:23:37+0100 [INFO] Blocked login detected:
  App      : Immich
  Email    : attacker@example.com
  IP       : 203.0.113.42
  Country  : CN
  IdP      : google
  Time     : 2026-03-20 18:20:23 CET
```

### Discord Notification

A rich embed with red color showing Application, Email, IP Address, Country, Identity Provider, and Time fields.

### Pushover Notification

```
CF Access blocked: Immich

App: Immich
Email: attacker@example.com
IP: 203.0.113.42
Country: CN
IdP: google
Time: 2026-03-20 18:20:23 CET
```

## Troubleshooting

Set `LOG_LEVEL=DEBUG` in `.env` and restart. Debug output shows the full request/response cycle with all secrets redacted.

| Symptom | Cause | Fix |
|---|---|---|
| `CF API HTTP 403` | Token lacks permissions | Recreate with Account > Access: Audit Logs > Read |
| `Discord HTTP 403` | Invalid webhook URL | Verify the full webhook URL in `.env` |
| Events not found | CF log ingestion delay (2-5 min) | Ensure `LOOKBACK_BUFFER` >= 600 |
| Duplicate alerts after reset | State volume was deleted | Expected on first run after reset |
| Missed events after downtime | Downtime exceeded `MAX_CATCHUP` | Increase `MAX_CATCHUP` value |

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](LICENSE) for the full text.