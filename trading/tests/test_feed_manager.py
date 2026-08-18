"""Tests for the background feed supervisor."""
from __future__ import annotations

import time

import pytest

from trading.src.config import FeedSettings
from trading.src.services.feed_manager import FeedManager


def wait_for(predicate, timeout: float = 5.0, interval: float = 0.02) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


@pytest.fixture
def collected() -> list:
    return []


def make_manager(settings: FeedSettings, sink: list, redis_client=None) -> FeedManager:
    return FeedManager(settings, on_frame=sink.append, redis_client=redis_client)


def test_synthetic_source_delivers_frames(feed_settings, collected):
    manager = make_manager(feed_settings, collected)
    manager.start()
    try:
        assert wait_for(lambda: len(collected) >= 3)
    finally:
        manager.stop()

    assert manager.status()["active_source"] == "synthetic"
    assert manager.status()["frames_received"] >= 3


def test_auto_source_falls_back_without_redis(feed_settings, collected):
    """A single container with no feeder and no Redis must still get data."""
    settings = FeedSettings(**{
        **feed_settings.__dict__,
        "source": "auto",
        "stale_after_seconds": 0.05,
    })
    manager = make_manager(settings, collected, redis_client=None)
    manager.start()
    try:
        assert wait_for(lambda: len(collected) >= 2)
        status = manager.status()
        assert "synthetic-fallback" in status["threads"]
    finally:
        manager.stop()

    assert status["configured_source"] == "auto"
    assert status["active_source"] == "synthetic"


def test_auto_fallback_keeps_a_steady_cadence(feed_settings, collected):
    """The standby generator must tick continuously, not once per stale window.

    Emitting only while stale left the demo book frozen between lurches.
    """
    settings = FeedSettings(**{
        **feed_settings.__dict__,
        "source": "auto",
        "synthetic_interval_seconds": 0.05,
        # Far longer than the run below, so a stale-only policy would emit once.
        "stale_after_seconds": 30.0,
    })
    manager = make_manager(settings, collected, redis_client=None)
    manager.start()
    try:
        assert wait_for(lambda: len(collected) >= 5), (
            f"fallback stalled after {len(collected)} frame(s)")
    finally:
        manager.stop()


def test_auto_fallback_yields_to_a_real_source(feed_settings, collected):
    """Real frames must win: the generator stops while another source is live."""
    settings = FeedSettings(**{
        **feed_settings.__dict__,
        "source": "auto",
        "synthetic_interval_seconds": 0.02,
        "stale_after_seconds": 5.0,
    })
    manager = make_manager(settings, collected, redis_client=None)
    manager.start()
    try:
        assert wait_for(lambda: len(collected) >= 2)

        # Simulate a live feeder frame arriving from Redis.
        manager._emit({"symbol": "BTC-USDT", "bids": [], "asks": []}, source="redis")
        settled = len(collected)
        time.sleep(0.3)  # Many synthetic intervals.

        assert len(collected) - settled <= 1, "generator kept competing with live data"
        assert manager.status()["active_source"] == "redis"
    finally:
        manager.stop()


def test_redis_source_without_client_starts_nothing(feed_settings, collected):
    settings = FeedSettings(**{**feed_settings.__dict__, "source": "redis"})
    manager = make_manager(settings, collected, redis_client=None)
    manager.start()
    try:
        time.sleep(0.2)
    finally:
        manager.stop()

    assert collected == []
    assert manager.status()["threads"] == []


def test_status_reports_no_frames_before_start(feed_settings, collected):
    manager = make_manager(feed_settings, collected)
    status = manager.status()

    assert status["frames_received"] == 0
    assert status["active_source"] == "none"
    assert status["last_frame_timestamp"] is None
    assert status["configured_source"] == "synthetic"


def test_stop_halts_frame_delivery(feed_settings, collected):
    manager = make_manager(feed_settings, collected)
    manager.start()
    assert wait_for(lambda: len(collected) >= 1)

    manager.stop()
    time.sleep(0.1)
    settled = len(collected)
    time.sleep(0.2)

    # At most one extra frame may land from an in-flight loop iteration.
    assert len(collected) - settled <= 1


def test_crashing_source_does_not_raise(feed_settings):
    def explode(_frame):
        raise RuntimeError("consumer failure")

    manager = FeedManager(feed_settings, on_frame=explode)
    manager.start()
    try:
        time.sleep(0.2)
    finally:
        manager.stop()

    # The guard logs and exits the thread rather than propagating.
    assert manager.status()["frames_received"] == 0
