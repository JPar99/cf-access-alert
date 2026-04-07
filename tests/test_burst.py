"""Tests for cf_access_alert.burst.BurstTracker."""

from datetime import UTC, datetime

import pytest

from cf_access_alert import config
from cf_access_alert.burst import BurstTracker


def make_event(ip: str, email: str = "user@example.com", app: str = "Immich",
               country: str = "us", created: datetime | None = None) -> dict:
    """Build a minimal blocked-event dict for testing."""
    if created is None:
        created = datetime.now(UTC)
    return {
        "ip_address": ip,
        "user_email": email,
        "app_name": app,
        "country": country,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ray_id": f"ray-{ip}-{created.timestamp()}",
    }


@pytest.fixture
def burst_config(monkeypatch):
    """Set predictable burst detection config for tests."""
    monkeypatch.setattr(config, "BURST_THRESHOLD", 5)
    monkeypatch.setattr(config, "BURST_WINDOW", 300)


class TestBurstTracker:
    def test_below_threshold_emits_individual_alerts(self, burst_config):
        tracker = BurstTracker()
        events = [make_event("1.2.3.4") for _ in range(3)]

        individual, bursts = tracker.classify(events)

        assert len(individual) == 3
        assert len(bursts) == 0

    def test_at_threshold_emits_burst(self, burst_config):
        tracker = BurstTracker()
        events = [make_event("1.2.3.4") for _ in range(5)]

        individual, bursts = tracker.classify(events)

        assert len(individual) == 0
        assert len(bursts) == 1
        assert bursts[0]["ip_address"] == "1.2.3.4"
        assert bursts[0]["count"] == 5
        assert bursts[0]["_burst"] is True

    def test_above_threshold_emits_burst(self, burst_config):
        tracker = BurstTracker()
        events = [make_event("1.2.3.4") for _ in range(10)]

        individual, bursts = tracker.classify(events)

        assert len(individual) == 0
        assert len(bursts) == 1
        assert bursts[0]["count"] == 10

    def test_different_ips_classified_independently(self, burst_config):
        tracker = BurstTracker()
        # 5 from one IP (burst), 2 from another (individual)
        events = (
            [make_event("1.2.3.4") for _ in range(5)]
            + [make_event("5.6.7.8") for _ in range(2)]
        )

        individual, bursts = tracker.classify(events)

        assert len(individual) == 2
        assert all(ev["ip_address"] == "5.6.7.8" for ev in individual)
        assert len(bursts) == 1
        assert bursts[0]["ip_address"] == "1.2.3.4"

    def test_burst_aggregates_emails_apps_countries(self, burst_config):
        tracker = BurstTracker()
        events = [
            make_event("1.2.3.4", email="a@x.com", app="Immich", country="cn"),
            make_event("1.2.3.4", email="b@x.com", app="Immich", country="cn"),
            make_event("1.2.3.4", email="a@x.com", app="Jellyfin", country="ru"),
            make_event("1.2.3.4", email="c@x.com", app="Jellyfin", country="cn"),
            make_event("1.2.3.4", email="a@x.com", app="Immich", country="cn"),
        ]

        _, bursts = tracker.classify(events)

        assert len(bursts) == 1
        burst = bursts[0]
        assert set(burst["emails"]) == {"a@x.com", "b@x.com", "c@x.com"}
        assert set(burst["apps"]) == {"Immich", "Jellyfin"}
        assert set(burst["countries"]) == {"CN", "RU"}

    def test_empty_batch_returns_empty(self, burst_config):
        tracker = BurstTracker()
        individual, bursts = tracker.classify([])
        assert individual == []
        assert bursts == []
