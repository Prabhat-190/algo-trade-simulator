"""Redis connection and order book pub/sub helpers shared by the app and feeders."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from ..config import RedisSettings

logger = logging.getLogger(__name__)

STREAM_PATTERN = "orderbook:*:stream"


def stream_channel(symbol: str) -> str:
    return f"orderbook:{symbol}:stream"


def latest_key(symbol: str) -> str:
    return f"orderbook:{symbol}:latest"


def connect(settings: RedisSettings, label: str = "redis") -> redis.Redis | None:
    """Connect to Redis with exponential backoff.

    Returns ``None`` instead of raising when Redis is unreachable so that every
    caller can degrade to in-process behaviour rather than crashing.
    """
    if not settings.configured:
        logger.info(
            "[%s] No Redis configured (set REDIS_URL or REDIS_HOST to enable it); "
            "using in-process state.", label,
        )
        return None

    delay = 1.0
    for attempt in range(1, settings.max_retries + 1):
        try:
            client = redis.Redis(
                host=settings.host,
                port=settings.port,
                password=settings.password,
                db=settings.db,
                decode_responses=True,
                socket_connect_timeout=settings.connect_timeout,
                socket_timeout=settings.connect_timeout,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            client.ping()
            logger.info("[%s] Connected to Redis at %s:%s", label, settings.host, settings.port)
            return client
        except (RedisConnectionError, RedisError, TimeoutError, OSError) as exc:
            logger.warning(
                "[%s] Redis connection attempt %d/%d failed: %s",
                label, attempt, settings.max_retries, exc,
            )
            if attempt < settings.max_retries:
                time.sleep(delay)
                delay *= 2

    logger.warning("[%s] Redis unavailable; continuing without it.", label)
    return None


def publish_orderbook(client: redis.Redis | None, orderbook: dict) -> bool:
    """Publish a frame to its stream and cache it as the latest snapshot."""
    if client is None:
        return False

    symbol = orderbook.get("symbol", "UNKNOWN")
    payload = json.dumps(orderbook)
    try:
        client.publish(stream_channel(symbol), payload)
        client.set(latest_key(symbol), payload, ex=300)
        return True
    except (RedisConnectionError, RedisError, TimeoutError) as exc:
        logger.error("Failed to publish %s order book: %s", symbol, exc)
        return False


def subscribe_orderbooks(
    client: redis.Redis,
    on_frame: Callable[[dict], None],
    stop_check: Callable[[], bool] | None = None,
) -> None:
    """Block on the order book stream, invoking ``on_frame`` per message.

    Reconnects on Redis errors so a transient outage does not silently kill the
    background thread that owns this loop.
    """
    while stop_check is None or not stop_check():
        try:
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.psubscribe(STREAM_PATTERN)
            logger.info("Subscribed to %s", STREAM_PATTERN)

            for message in pubsub.listen():
                if stop_check is not None and stop_check():
                    pubsub.close()
                    return
                if message.get("type") != "pmessage":
                    continue
                try:
                    on_frame(json.loads(message["data"]))
                except (ValueError, TypeError) as exc:
                    logger.error("Discarding malformed order book frame: %s", exc)
        except (RedisConnectionError, RedisError, TimeoutError) as exc:
            logger.error("Redis subscription dropped (%s); retrying in 5s", exc)
            time.sleep(5)
