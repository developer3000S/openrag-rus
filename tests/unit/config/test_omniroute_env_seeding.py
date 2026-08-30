"""Unit tests for the OMNIROUTE provider env seeding."""

import tempfile
from pathlib import Path

from config.config_manager import ConfigManager


def _load(monkeypatch, **env):
    for key in ("OMNIROUTE_API_KEY", "OMNIROUTE_HOST", "OMNIROUTE_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_file = Path(tmp) / "config.yaml"
        cm = ConfigManager(config_file=str(cfg_file))
        return cm.load_config()


def test_omniroute_env_seeds_custom_provider(monkeypatch):
    config = _load(
        monkeypatch,
        OMNIROUTE_API_KEY="omni-secret",
        OMNIROUTE_HOST="https://omni.internal/api/v1",
    )

    stored = config.providers.custom.get("omniroute")
    assert stored is not None
    assert stored.configured is True
    assert config.providers.credential_values("omniroute") == {
        "api_key": "omni-secret",
        "api_base": "https://omni.internal/api/v1",
    }
    assert config.providers.any_configured() is True


def test_omniroute_env_strips_stray_quotes(monkeypatch):
    """`OMNIROUTE_HOST` sometimes ships with a trailing quote; tolerate it."""
    config = _load(
        monkeypatch,
        OMNIROUTE_API_KEY="omni-secret",
        OMNIROUTE_HOST="http://omni.internal/api/v1\"",
    )

    values = config.providers.credential_values("omniroute")
    assert values["api_base"] == "http://omni.internal/api/v1"


def test_omniroute_without_env_is_not_configured(monkeypatch):
    config = _load(monkeypatch)
    assert "omniroute" not in config.providers.custom
    assert config.providers.any_configured() is False