# Notifications

cf-access-alert supports three notification channels. You can use any combination — at least one must be configured.

## Pushover

[Pushover](https://pushover.net/) delivers push notifications to iOS, Android, and desktop.

### Setup

1. Create an account at [pushover.net](https://pushover.net/)
2. Create an application to get an API token
3. Add to `.env`:

```
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_APP_TOKEN=your_app_token
PUSHOVER_PRIORITY=0
PUSHOVER_SOUND=pushover
```

### Example notification

```
CF Access blocked: Immich

App: Immich
Email: attacker@example.com
IP: 203.0.113.42
Country: CN
IdP: google
Time: 2026-03-20 18:20:23 CET
```

## Discord

Sends rich embed messages via [Discord webhooks](https://support.discord.com/hc/en-us/articles/228383668).

### Setup

1. In your Discord server, go to **Server Settings > Integrations > Webhooks**
2. Create a new webhook and copy the URL
3. Add to `.env`:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Example notification

A rich embed with red color showing Application, Email, IP Address, Country, Identity Provider, and Time fields.

## ntfy

[ntfy](https://ntfy.sh/) is a simple HTTP-based pub-sub notification service popular with self-hosters. Works with the public ntfy.sh server or your own self-hosted instance.

### Setup (ntfy.sh)

1. Pick a topic name (this is essentially a password — choose something not easily guessable)
2. Subscribe to it in the ntfy app on your phone
3. Add to `.env`:

```
NTFY_TOPIC=your-secret-topic-name
```

### Setup (self-hosted)

```
NTFY_URL=https://ntfy.yourdomain.com
NTFY_TOPIC=your-topic
NTFY_TOKEN=your-bearer-token
```

### Priority

ntfy priority levels: 1 (min), 2 (low), 3 (default), 4 (high), 5 (max). Default is `4`.

```
NTFY_PRIORITY=4
```

## Burst Alerts

When burst detection triggers (same IP blocked ≥ `BURST_THRESHOLD` times within `BURST_WINDOW`), all channels receive a brute-force summary instead of individual alerts:

```
⚠ Brute-force: 203.0.113.42

IP: 203.0.113.42
Blocked attempts: 14 in 5m
Emails: attacker@example.com
Apps: Immich, Jellyfin
Countries: CN
```

## Daily Digest

When enabled, a daily summary is sent to all channels at `DIGEST_TIME`:

```
📊 CF Access daily digest

Daily summary:
  Total blocked: 47
  Burst alerts: 3
  Unique IPs: 12
  Unique emails: 8

  Top IPs:
    203.0.113.42: 14
    198.51.100.7: 9
  Top emails:
    attacker@example.com: 23
  Top apps:
    Immich: 31
    Jellyfin: 16
  Top countries:
    CN: 28
    RU: 12
```

## Retry Behavior

All notification channels share the same retry settings. On failure, notifications retry with exponential backoff:

- Attempt 1: immediate
- Attempt 2: after `NOTIFY_RETRY_DELAY` (default 10s)
- Attempt 3: after `NOTIFY_RETRY_DELAY × 2` (default 20s)

Configure with `NOTIFY_RETRIES` and `NOTIFY_RETRY_DELAY`.
