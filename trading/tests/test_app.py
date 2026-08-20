"""App / health endpoint tests."""
from __future__ import annotations

import time

import pytest

from trading.src.app import create_app


@pytest.fixture(scope="module")
def app(offline_settings_module):
    """App instance with synthetic feed running."""
    instance = create_app(offline_settings_module)
    # Give the synthetic feed time to publish a first frame.
    deadline = time.time() + 5
    while time.time() < deadline and instance.market.last_update_time == 0:
        time.sleep(0.02)
    yield instance
    instance.feed_manager.stop()


@pytest.fixture(scope="module")
def offline_settings_module():
    from trading.src.config import FeedSettings, RedisSettings, Settings
    return Settings(
        port=0,
        redis=RedisSettings(host="127.0.0.1", port=1, max_retries=1, connect_timeout=0.05),
        feed=FeedSettings(
            source="synthetic",
            symbol="TEST-USDT",
            exchange="TESTNET",
            synthetic_interval_seconds=0.01,
            synthetic_start_price=1000.0,
            synthetic_depth=5,
        ),
    )


@pytest.fixture
def client(app):
    return app.server.test_client()


def test_app_starts_without_redis(app):
    """Redis down should not crash the app."""
    assert app.redis_client is None
    assert app.project_store is not None


def test_app_starts_quickly_when_redis_is_unconfigured(offline_settings_module):
    """Dont hang on redis if it was never configured."""
    from dataclasses import replace

    from trading.src.config import RedisSettings

    settings = replace(
        offline_settings_module,
        # An unroutable address: any real attempt would hang until timeout.
        redis=RedisSettings(host="10.255.255.1", port=6379, max_retries=3,
                            connect_timeout=5.0, configured=False),
    )

    started = time.monotonic()
    instance = create_app(settings)
    try:
        elapsed = time.monotonic() - started
        assert elapsed < 5.0, f"startup took {elapsed:.1f}s"
        assert instance.redis_client is None
        assert instance.health_payload()["redis"]["status"] == "not_configured"
    finally:
        instance.feed_manager.stop()


def test_market_data_arrives_from_embedded_feed(app):
    assert app.market.last_update_time > 0
    assert app.market.snapshot()["mid_price"] > 0


def test_healthz_reports_ok(client):
    response = client.get("/healthz")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["redis"]["status"] == "not_configured"
    assert payload["market_data"]["status"] == "fresh"
    assert payload["feed"]["active_source"] == "synthetic"


def test_readyz_is_ready_once_data_flows(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.get_json()["ready"] is True


def test_index_page_renders(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Algo Trade Simulator" in body


def test_theme_stylesheet_is_served(client, app):
    # Dash fingerprints assets; /assets/theme.css still works
    assets = app.dashboard.app.config.assets_folder
    assert assets.endswith("assets")

    response = client.get("/assets/theme.css")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "--accent" in body
    assert ".container-fluid" in body
    assert ".btn-primary" in body


def test_simulation_runs_against_live_synthetic_book(app):
    mid_price = app.market.snapshot()["mid_price"]
    result = app.market.simulate_market_order(
        side="buy", quantity=100 / mid_price, exchange="OKX",
        market_type="spot", fee_tier="VIP0", volatility=0.01,
    )

    assert "error" not in result
    assert result["net_cost"] > 0
    # $100 order should be a fraction of a percent, not like 5%
    assert result["net_cost_percentage"] < 1.0


def test_readyz_is_unavailable_when_data_is_stale(offline_settings_module):
    """No feed => not ready."""
    instance = create_app(offline_settings_module, start_feeds=False)
    try:
        client = instance.server.test_client()
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 503
    finally:
        instance.feed_manager.stop()
