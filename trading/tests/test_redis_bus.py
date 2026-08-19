"""Tests for the Redis pub/sub helpers."""
from __future__ import annotations

import json
import time

from redis.exceptions import RedisError

from trading.src.config import RedisSettings
from trading.src.data import redis_bus


class FakeRedis:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.published: list[tuple[str, str]] = []
        self.values: dict[str, str] = {}

    def publish(self, channel: str, payload: str) -> None:
        if self.fail:
            raise RedisError("publish failed")
        self.published.append((channel, payload))

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self.fail:
            raise RedisError("set failed")
        self.values[key] = value


def test_channel_and_key_naming():
    assert redis_bus.stream_channel("BTC-USDT") == "orderbook:BTC-USDT:stream"
    assert redis_bus.latest_key("BTC-USDT") == "orderbook:BTC-USDT:latest"


def test_publish_writes_stream_and_snapshot():
    client = FakeRedis()
    frame = {"symbol": "BTC-USDT", "asks": [[1.0, 1.0]], "bids": [[0.9, 1.0]]}

    assert redis_bus.publish_orderbook(client, frame) is True
    channel, payload = client.published[0]
    assert channel == "orderbook:BTC-USDT:stream"
    assert json.loads(payload) == frame
    assert "orderbook:BTC-USDT:latest" in client.values


def test_publish_without_client_is_a_noop():
    assert redis_bus.publish_orderbook(None, {"symbol": "X"}) is False


def test_publish_reports_failure_instead_of_raising():
    assert redis_bus.publish_orderbook(FakeRedis(fail=True), {"symbol": "X"}) is False


def test_frame_without_symbol_uses_placeholder():
    client = FakeRedis()
    redis_bus.publish_orderbook(client, {"asks": [], "bids": []})
    assert client.published[0][0] == "orderbook:UNKNOWN:stream"


def test_connect_returns_none_when_unreachable():
    settings = RedisSettings(
        host="127.0.0.1", port=1, max_retries=1, connect_timeout=0.05, configured=True)
    assert redis_bus.connect(settings, label="test") is None


def test_connect_skips_immediately_when_not_configured():
    """Unconfigured Redis must return instantly rather than retrying.

    Guards the regression where startup spent ~11s on backoff retries against a
    default localhost address, delaying the first response past the health check.
    """
    settings = RedisSettings(host="10.255.255.1", port=6379, max_retries=5,
                             connect_timeout=5.0, configured=False)

    started = time.monotonic()
    assert redis_bus.connect(settings, label="test") is None
    assert time.monotonic() - started < 0.5


def test_subscribe_dispatches_frames_and_honours_stop():
    frame = {"symbol": "BTC-USDT", "asks": [], "bids": []}
    messages = [
        {"type": "subscribe", "data": 1},
        {"type": "pmessage", "data": json.dumps(frame)},
        {"type": "pmessage", "data": "not-json"},
        {"type": "pmessage", "data": json.dumps(frame)},
    ]
    received: list[dict] = []
    calls = {"count": 0}

    class PubSub:
        def psubscribe(self, _pattern):
            pass

        def listen(self):
            yield from messages

        def close(self):
            pass

    class Client:
        def pubsub(self, **_kwargs):
            return PubSub()

    def stop_check() -> bool:
        # Stop once both valid frames have been handled.
        calls["count"] += 1
        return len(received) >= 2

    redis_bus.subscribe_orderbooks(Client(), on_frame=received.append, stop_check=stop_check)

    assert received == [frame, frame]
