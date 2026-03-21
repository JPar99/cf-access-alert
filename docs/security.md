# Security

This container is designed with security as the top priority.

## Container Hardening

- **Non-root execution** — runs as `appuser` inside the container
- **Read-only filesystem** — `read_only: true` with minimal tmpfs for `/tmp`
- **No privileges** — `no-new-privileges` security option
- **No exposed ports** — outbound-only HTTP requests, no listening sockets
- **No Docker socket** — no access to the host Docker daemon
- **Resource limits** — capped at 64 MB RAM and 0.25 CPU
- **Zero dependencies** — Python stdlib only, minimal attack surface

## Secret Handling

- **Secrets from `.env` only** — never from CLI arguments, config files, or labels
- **No secret leakage in logs** — all sensitive values (API tokens, webhook URLs, user keys) are redacted in every log line, including in debug mode
- **`.dockerignore`** — secrets excluded from build context
- **`.gitignore`** — `.env` excluded from version control

### Recommended `.env` permissions

```bash
chmod 600 .env
chown root:root .env  # or your deploy user
```

## HEALTHCHECK Without Attack Surface

Unlike many monitoring tools that open an HTTP port for health checks, cf-access-alert uses Docker's native `HEALTHCHECK` instruction. The health check script runs inside the container and checks state file freshness — no network listener, no port, no inbound attack surface.

## Docker Compose Reference

```yaml
services:
  cf-access-alert:
    container_name: cf-access-alert
    image: ghcr.io/jpar99/cf-access-alert:latest
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
