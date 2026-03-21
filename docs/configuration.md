# Configuration

All configuration is done through environment variables in the `.env` file.

## Required Variables

| Variable | Description |
|---|---|
| `CF_API_TOKEN` | Cloudflare API token with **Account > Access: Audit Logs > Read** permission |
| `CF_ACCOUNT_ID` | Your Cloudflare account ID (found on domain Overview page) |

At least one notification channel must be configured:

| Variable | Description |
|---|---|
| `PUSHOVER_USER_KEY` | Pushover user key |
| `PUSHOVER_APP_TOKEN` | Pushover application API token (required when using Pushover) |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL |
| `NTFY_TOPIC` | ntfy topic name (enables ntfy) |

## Optional Variables

### Cloudflare

| Variable | Default | Description |
|---|---|---|
| `CF_APP_UIDS` | *(empty — all apps)* | Comma-separated Access application UUIDs to monitor |

### Notifications

| Variable | Default | Description |
|---|---|---|
| `PUSHOVER_PRIORITY` | `0` | Pushover priority: `-1` (silent), `0` (normal), `1` (high) |
| `PUSHOVER_SOUND` | `pushover` | Pushover notification sound |
| `NTFY_URL` | `https://ntfy.sh` | ntfy server URL (for self-hosted instances) |
| `NTFY_TOKEN` | *(empty)* | ntfy bearer token for authentication |
| `NTFY_PRIORITY` | `4` | ntfy priority: 1 (min) to 5 (max), default 4 (high) |

### Burst Detection

| Variable | Default | Description |
|---|---|---|
| `BURST_THRESHOLD` | `5` | Number of blocks from the same IP to trigger burst mode |
| `BURST_WINDOW` | `5m` | Time window for burst detection |

### Daily Digest

| Variable | Default | Description |
|---|---|---|
| `DIGEST_ENABLED` | `true` | Enable or disable the daily digest |
| `DIGEST_TIME` | `08:00` | Local time (HH:MM) to send the daily digest |

### Polling

| Variable | Default | Description |
|---|---|---|
| `POLL_INTERVAL` | `5m` | How often to poll Cloudflare Access logs |
| `LOOKBACK_BUFFER` | `10m` | How far back to look each poll (accounts for CF log delay) |
| `MAX_CATCHUP` | `7d` | Max catchup window after container downtime |

### Retry

| Variable | Default | Description |
|---|---|---|
| `NOTIFY_RETRIES` | `3` | Number of retry attempts per notification |
| `NOTIFY_RETRY_DELAY` | `10s` | Base delay between retries (doubles each attempt) |

### General

| Variable | Default | Description |
|---|---|---|
| `TZ` | `Europe/Amsterdam` | Timezone for logs and notifications |
| `LOG_LEVEL` | `INFO` | Log level: `INFO` or `DEBUG` |

Duration values support: `30s`, `10m`, `2h`, `7d`. Plain numbers are treated as seconds.

## Creating a Cloudflare API Token

1. Go to [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **Create Token** > **Create Custom Token**
3. Set permissions: **Account > Access: Audit Logs > Read**
4. Restrict to your specific account under Account Resources
5. Create and copy the token (shown only once)

## Filtering by Application

Cloudflare Access apps have two identifiers in the API:

- **`app_domain`** — for SaaS-type apps this is your `.cloudflareaccess.com` domain, not the actual app hostname
- **`app_uid`** — the UUID assigned by Cloudflare (more reliable for filtering)

To find your app's UID, query the API:

```bash
curl -s "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/access/logs/access_requests?limit=1" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool
```

To monitor multiple apps, comma-separate the UIDs:

```
CF_APP_UIDS=uid-one-here,uid-two-here,uid-three-here
```
