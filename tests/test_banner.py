"""Tests for cf_access_alert.banner VERSION resolution."""

import importlib

import pytest


@pytest.fixture
def reload_banner(monkeypatch):
    """Reload banner module after env/file mutations so _resolve_version re-runs."""

    def _reload():
        import cf_access_alert.banner

        return importlib.reload(cf_access_alert.banner)

    return _reload


class TestVersionResolution:
    def test_env_var_takes_precedence(self, reload_banner, monkeypatch):
        monkeypatch.setenv("CF_ACCESS_ALERT_VERSION", "9.9.9-test")
        banner = reload_banner()
        assert banner.VERSION == "9.9.9-test"

    def test_env_var_strips_whitespace(self, reload_banner, monkeypatch):
        monkeypatch.setenv("CF_ACCESS_ALERT_VERSION", "  1.2.3  ")
        banner = reload_banner()
        assert banner.VERSION == "1.2.3"

    def test_empty_env_var_falls_through_to_file(self, reload_banner, monkeypatch):
        monkeypatch.setenv("CF_ACCESS_ALERT_VERSION", "")
        banner = reload_banner()
        # Should fall back to the VERSION file at the repo root
        assert banner.VERSION != ""
        assert banner.VERSION != "0.0.0-dev"

    def test_file_used_when_env_unset(self, reload_banner, monkeypatch):
        monkeypatch.delenv("CF_ACCESS_ALERT_VERSION", raising=False)
        banner = reload_banner()
        # Should resolve to whatever the VERSION file currently contains
        assert banner.VERSION != ""
        assert banner.VERSION != "0.0.0-dev"

    def test_version_is_non_empty_string(self, reload_banner, monkeypatch):
        monkeypatch.delenv("CF_ACCESS_ALERT_VERSION", raising=False)
        banner = reload_banner()
        assert isinstance(banner.VERSION, str)
        assert len(banner.VERSION) > 0
