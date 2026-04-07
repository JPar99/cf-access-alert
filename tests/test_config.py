"""Tests for cf_access_alert.config helpers."""

from cf_access_alert.config import parse_duration, redact_url


class TestParseDuration:
    def test_seconds_suffix(self):
        assert parse_duration("30s", 0) == 30

    def test_minutes_suffix(self):
        assert parse_duration("5m", 0) == 300

    def test_hours_suffix(self):
        assert parse_duration("2h", 0) == 7200

    def test_days_suffix(self):
        assert parse_duration("7d", 0) == 604800

    def test_plain_integer_treated_as_seconds(self):
        assert parse_duration("90", 0) == 90

    def test_empty_string_returns_default(self):
        assert parse_duration("", 42) == 42

    def test_whitespace_only_returns_default(self):
        assert parse_duration("   ", 42) == 42

    def test_invalid_returns_default(self):
        assert parse_duration("not-a-duration", 99) == 99

    def test_invalid_unit_returns_default(self):
        assert parse_duration("10y", 99) == 99

    def test_uppercase_unit_normalized(self):
        assert parse_duration("5M", 0) == 300

    def test_internal_whitespace_allowed(self):
        assert parse_duration("10 m", 0) == 600


class TestRedactUrl:
    def test_redacts_cloudflare_account_id(self):
        url = "https://api.cloudflare.com/client/v4/accounts/abc123def456/access/logs"
        result = redact_url(url)
        assert "abc123def456" not in result
        assert "REDACTED" in result

    def test_redacts_discord_webhook_token(self):
        url = "https://discord.com/api/webhooks/123456/aBcDeFgHiJ-kLmNoPqRsTuVwXyZ"
        result = redact_url(url)
        assert "aBcDeFgHiJ-kLmNoPqRsTuVwXyZ" not in result
        assert "REDACTED" in result
        # Webhook ID itself should be preserved
        assert "/webhooks/123456/" in result

    def test_leaves_clean_url_alone(self):
        url = "https://ntfy.sh/my-topic"
        assert redact_url(url) == url

    def test_redacts_both_in_same_string(self):
        url = (
            "https://api.cloudflare.com/client/v4/accounts/deadbeef0123/access "
            "https://discord.com/api/webhooks/999/secrettoken"
        )
        result = redact_url(url)
        assert "deadbeef0123" not in result
        assert "secrettoken" not in result
