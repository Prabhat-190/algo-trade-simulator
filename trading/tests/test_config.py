"""Tests for environment-driven configuration."""
from __future__ import annotations

import pytest

from trading.src.config import (
    DEFAULT_WEBSOCKET_URI,
    FEED_AUTO,
    FeedSettings,
    RedisSettings,
    Settings,
    StockFeedSettings,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove every variable the config reads so defaults are observable."""
    for name in (
        "HOST", "PORT", "DEBUG", "LOG_LEVEL", "MODELS_DIR", "HEALTH_STALE_AFTER_SECONDS",
        "REDIS_URL", "REDIS_PRIVATE_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
        "REDIS_DB", "REDIS_MAX_RETRIES", "REDIS_CONNECT_TIMEOUT",
        "FEED_SOURCE", "WEBSOCKET_URI", "SYMBOL", "EXCHANGE", "FEED_STALE_AFTER_SECONDS",
        "SYNTHETIC_INTERVAL_SECONDS", "SYNTHETIC_START_PRICE", "SYNTHETIC_VOLATILITY",
        "SYNTHETIC_DEPTH", "SYNTHETIC_SPREAD_BPS",
        "STOCK_SYMBOL", "STOCK_PROVIDER", "STOCK_POLL_INTERVAL",
        "FINNHUB_API_KEY", "ALPHA_VANTAGE_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_are_deployment_safe():
    settings = Settings.from_env()

    assert settings.host == "0.0.0.0"
    assert settings.port == 8050
    assert settings.debug is False
    # "auto" is what keeps a single-service deploy populated.
    assert settings.feed.source == FEED_AUTO
    assert settings.feed.websocket_uri == DEFAULT_WEBSOCKET_URI


def test_port_and_host_come_from_env(monkeypatch):
    monkeypatch.setenv("PORT", "7860")
    monkeypatch.setenv("HOST", "127.0.0.1")
    settings = Settings.from_env()

    assert settings.port == 7860
    assert settings.host == "127.0.0.1"


def test_invalid_numeric_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-port")
    assert Settings.from_env().port == 8050


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True),
    ("0", False), ("false", False), ("", False), ("maybe", False),
])
def test_debug_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("DEBUG", value)
    assert Settings.from_env().debug is expected


def test_redis_is_not_configured_by_default():
    """Nothing set means Redis must not be attempted at all.

    Retrying an unconfigured default delayed the first response by ~11s and made
    platform health checks fail the deploy.
    """
    settings = RedisSettings.from_env()

    assert settings.configured is False
    assert settings.max_retries <= 2
    assert settings.connect_timeout <= 2.0


def test_setting_redis_host_marks_it_configured(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "cache")
    assert RedisSettings.from_env().configured is True


def test_setting_redis_url_marks_it_configured(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379")
    assert RedisSettings.from_env().configured is True


def test_redis_port_alone_does_not_enable_redis(monkeypatch):
    """A stray REDIS_PORT should not trigger connection attempts on localhost."""
    monkeypatch.setenv("REDIS_PORT", "6379")
    assert RedisSettings.from_env().configured is False


def test_redis_url_is_parsed(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://:s3cret@redis.internal:6380/2")
    redis_settings = RedisSettings.from_env()

    assert redis_settings.host == "redis.internal"
    assert redis_settings.port == 6380
    assert redis_settings.password == "s3cret"
    assert redis_settings.db == 2


def test_redis_url_takes_precedence_over_host_pair(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "ignored")
    monkeypatch.setenv("REDIS_URL", "redis://managed:6379")
    assert RedisSettings.from_env().host == "managed"


def test_redis_host_pair_used_without_url(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "cache")
    monkeypatch.setenv("REDIS_PORT", "6399")
    redis_settings = RedisSettings.from_env()

    assert redis_settings.host == "cache"
    assert redis_settings.port == 6399


def test_unknown_feed_source_falls_back_to_auto(monkeypatch):
    monkeypatch.setenv("FEED_SOURCE", "carrier-pigeon")
    assert FeedSettings.from_env().source == FEED_AUTO


def test_feed_source_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("FEED_SOURCE", "SYNTHETIC")
    assert FeedSettings.from_env().source == "synthetic"


def test_stock_settings_pick_matching_api_key(monkeypatch):
    monkeypatch.setenv("STOCK_PROVIDER", "alphavantage")
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "av-key")
    monkeypatch.setenv("FINNHUB_API_KEY", "fh-key")

    settings = StockFeedSettings.from_env()
    assert settings.provider == "alphavantage"
    assert settings.api_key == "av-key"


def test_stock_symbol_is_upper_cased(monkeypatch):
    monkeypatch.setenv("STOCK_SYMBOL", "aapl")
    assert StockFeedSettings.from_env().symbol == "AAPL"
