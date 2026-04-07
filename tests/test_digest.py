"""Tests for cf_access_alert.digest scheduling helpers."""

from datetime import UTC, datetime, timedelta

import pytest

from cf_access_alert import config
from cf_access_alert.digest import compute_next_digest


@pytest.fixture
def digest_at_8am(monkeypatch):
    """Pin DIGEST_HOUR=8, DIGEST_MINUTE=0."""
    monkeypatch.setattr(config, "DIGEST_HOUR", 8)
    monkeypatch.setattr(config, "DIGEST_MINUTE", 0)


class TestComputeNextDigest:
    def test_before_target_schedules_today(self, digest_at_8am):
        # 06:00 local on 2026-04-07 — digest should fire at 08:00 same day
        now = datetime(2026, 4, 7, 6, 0, 0, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.year == 2026
        assert next_dt.month == 4
        assert next_dt.day == 7
        assert next_dt.hour == 8
        assert next_dt.minute == 0

    def test_after_target_schedules_tomorrow(self, digest_at_8am):
        # 14:00 local on 2026-04-07 — digest should fire at 08:00 next day
        now = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.day == 8
        assert next_dt.hour == 8

    def test_exactly_at_target_schedules_tomorrow(self, digest_at_8am):
        # 08:00:00 exactly — target <= now, so push to tomorrow
        now = datetime(2026, 4, 7, 8, 0, 0, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.day == 8
        assert next_dt.hour == 8

    def test_one_second_after_target_schedules_tomorrow(self, digest_at_8am):
        now = datetime(2026, 4, 7, 8, 0, 1, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.day == 8

    def test_one_second_before_target_schedules_today(self, digest_at_8am):
        now = datetime(2026, 4, 7, 7, 59, 59, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.day == 7
        assert next_dt.hour == 8

    def test_month_boundary(self, digest_at_8am):
        # 23:00 on the last day of month — digest fires at 08:00 next day (next month)
        now = datetime(2026, 3, 31, 23, 0, 0, tzinfo=UTC)
        next_dt = compute_next_digest(now)

        assert next_dt.month == 4
        assert next_dt.day == 1
        assert next_dt.hour == 8

    def test_preserves_timezone(self, digest_at_8am):
        now = datetime(2026, 4, 7, 6, 0, 0, tzinfo=UTC)
        next_dt = compute_next_digest(now)
        assert next_dt.tzinfo is not None

    def test_difference_at_most_24h(self, digest_at_8am):
        # No matter when "now" is, next digest should be within 24 hours
        now = datetime(2026, 4, 7, 8, 0, 1, tzinfo=UTC)
        next_dt = compute_next_digest(now)
        assert (next_dt - now) <= timedelta(hours=24)
