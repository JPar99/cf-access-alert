# Troubleshooting

## Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` and restart. Debug output shows the full request/response cycle with all secrets redacted.

```bash
docker compose restart
docker compose logs -f
```

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `CF API HTTP 403` | Token lacks permissions | Recreate with **Account > Access: Audit Logs > Read** |
| `Discord HTTP 403` | Invalid webhook URL | Verify the full webhook URL in `.env` |
| `ntfy HTTP 401` | Invalid or missing token | Check `NTFY_TOKEN` for self-hosted instances |
| Events not found | CF log ingestion delay (2–5 min) | Ensure `LOOKBACK_BUFFER` >= `10m` |
| Duplicate alerts after reset | State volume was deleted | Expected on first run after reset |
| Missed events after downtime | Downtime exceeded `MAX_CATCHUP` | Increase `MAX_CATCHUP` value |
| Digest not sending | `DIGEST_TIME` already passed | Rebuild — schedule recalculates on startup |
| HEALTHCHECK unhealthy | Poller stopped or state file stale | Check logs for API errors |

## Useful Commands

```bash
# Start
docker compose up -d

# Build and start locally
docker compose up -d --build

# View logs (follow)
docker compose logs -f

# Check health status
docker inspect --format='{{.State.Health.Status}}' cf-access-alert

# Restart after .env changes
docker compose down
docker compose up -d --build

# Reset state (will re-alert on recent events)
docker compose down
docker volume rm cf-access-alert_cf-access-alert-data
docker compose up -d

# Graceful stop (saves state)
docker compose down
```
