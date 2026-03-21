"""Cloudflare Access API — fetch and filter authentication logs."""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from . import config
from .banner import VERSION
from .config import redact_url

log = logging.getLogger("cf-access-alert")

USER_AGENT = f"cf-access-alert/{VERSION}"


def _fetch_page(since: str, until: str, page: int) -> dict | None:
    """Fetch a single page of Access logs. Returns parsed JSON body or None."""
    base = (
        f"https://api.cloudflare.com/client/v4/accounts/{config.CF_ACCOUNT_ID}"
        f"/access/logs/access_requests"
    )
    params = (
        f"since={since}&until={until}"
        f"&limit={config.CF_PAGE_SIZE}&direction=asc&page={page + 1}"
    )
    url = f"{base}?{params}"

    log.debug("CF API request: GET %s (page %d)", redact_url(url), page + 1)

    req = Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {config.CF_API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)

    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            log.debug("CF API response: HTTP %s, success=%s, result_count=%d",
                      resp.status, body.get("success"), len(body.get("result", [])))
            return body
    except HTTPError as exc:
        log.error("Cloudflare API HTTP %s — check token permissions", exc.code)
        return None
    except URLError as exc:
        log.error("Cloudflare API connection error: %s", exc.reason)
        return None
    except Exception:
        log.exception("Unexpected error calling Cloudflare API")
        return None


def fetch_logs(since: str, until: str, shutdown=None) -> list[dict]:
    """
    Fetch all Access log events between since and until.
    Paginates automatically if there are more than CF_PAGE_SIZE results.
    """
    all_events = []
    page = 0
    max_pages = 50  # safety cap: 50 * 100 = 5000 events

    while page < max_pages:
        if shutdown and shutdown.should_exit:
            break

        body = _fetch_page(since, until, page)
        if body is None:
            break

        if not body.get("success"):
            errors = body.get("errors", [])
            for e in errors:
                log.error("CF API error %s: %s", e.get("code"), e.get("message"))
            break

        results = body.get("result", [])

        for ev in results:
            log.debug("  Event: email=%s allowed=%s action=%s app=%s created=%s",
                      ev.get("user_email"), ev.get("allowed"), ev.get("action"),
                      ev.get("app_name", ev.get("app_domain")), ev.get("created_at"))

        all_events.extend(results)

        if len(results) < config.CF_PAGE_SIZE:
            break

        page += 1
        if page < max_pages:
            log.debug("Fetching next page (%d events so far)", len(all_events))

    if page >= max_pages:
        log.warning("Hit pagination limit (%d pages, %d events). "
                    "Some events may be missed.", max_pages, len(all_events))

    log.debug("Total events fetched: %d", len(all_events))
    return all_events


def filter_events(events: list[dict]) -> list[dict]:
    """Keep only events where allowed is False (blocked by CF Access)."""
    log.debug("Filtering %d event(s)", len(events))
    matched = []

    for ev in events:
        allowed = ev.get("allowed")

        if allowed is not False:
            log.debug("  SKIP (allowed): email=%s allowed=%s action=%s",
                      ev.get("user_email"), allowed, ev.get("action"))
            continue

        if config.CF_APP_UIDS:
            if ev.get("app_uid", "") not in config.CF_APP_UIDS:
                log.debug("  SKIP (UID mismatch): event=%s not in filter set",
                          ev.get("app_uid"))
                continue

        log.debug("  MATCH: email=%s allowed=%s app=%s",
                  ev.get("user_email"), allowed,
                  ev.get("app_name", ev.get("app_domain")))
        matched.append(ev)

    return matched