# cf-access-alert

Lightweight Docker container that monitors [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/) authentication logs and sends real-time alerts when login attempts are blocked.

Built for homelabs and self-hosters protecting apps like Immich, Jellyfin, and Dawarich behind Cloudflare Access.

## Features

- **Real-time alerts** via Pushover, Discord, and ntfy.sh (or self-hosted ntfy)
- **Burst detection** — groups rapid blocked attempts from the same IP into a single brute-force alert
- **Daily digest** — configurable daily summary of all blocked events
- **Docker HEALTHCHECK** — reports healthy/unhealthy to Docker without opening any port
- **Downtime catchup** — on restart, catches up on missed events (up to 7 days)
- **Deduplication** — tracks alerted events by `ray_id` to prevent duplicates
- **Security-first** — non-root, read-only filesystem, no exposed ports, secrets never in logs
- **Zero dependencies** — Python stdlib only, ~70 MB image

## Quick Start

```bash
mkdir cf-access-alert && cd cf-access-alert
curl -LO https://raw.githubusercontent.com/jpar99/cf-access-alert/main/docker-compose.yml
curl -LO https://raw.githubusercontent.com/jpar99/cf-access-alert/main/.env.example
cp .env.example .env
chmod 600 .env
nano .env  # fill in your tokens
docker compose up -d
```

Or build locally:

```bash
git clone https://github.com/jpar99/cf-access-alert.git
cd cf-access-alert
cp .env.example .env && chmod 600 .env && nano .env
docker compose up -d --build
```

## Configuration

All settings are environment variables in `.env`. See [docs/configuration.md](docs/configuration.md) for the full reference.

The minimum required:

| Variable | Description |
|---|---|
| `CF_API_TOKEN` | Cloudflare API token ([how to create](docs/configuration.md#creating-a-cloudflare-api-token)) |
| `CF_ACCOUNT_ID` | Your Cloudflare account ID |
| One of: `PUSHOVER_USER_KEY`, `DISCORD_WEBHOOK_URL`, or `NTFY_TOPIC` | At least one notification channel |

## Documentation

| Document | Description |
|---|---|
| [Configuration](docs/configuration.md) | All environment variables, API token setup, app filtering |
| [Notifications](docs/notifications.md) | Pushover, Discord, ntfy setup and examples |
| [Features](docs/features.md) | Burst detection, daily digest, downtime recovery |
| [Security](docs/security.md) | Container hardening, secret handling |
| [Troubleshooting](docs/troubleshooting.md) | Common issues, debug mode, useful commands |

## How It Works

```
┌──────────────────┐    poll every 5m    ┌──────────────────┐
│                  │ ──────────────────> │                  │
│  cf-access-alert │                     │  Cloudflare API  │
│                  │ <────────────────── │  Access Logs     │
└────────┬─────────┘   blocked events    └──────────────────┘
         │
         ├─ deduplicate by ray_id
         ├─ burst detection (group rapid attempts)
         │
         ├──────> Pushover
         ├──────> Discord
         └──────> ntfy
         
         Daily digest ──> all channels at DIGEST_TIME
```

## License

GNU GPL v3 — see [LICENSE](LICENSE).