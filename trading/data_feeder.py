"""Crypto order book feeder.

Streams L2 order book frames from an exchange WebSocket into Redis so one or
more dashboard replicas can share a single upstream connection. Only needed for
multi-service deployments; a single container can use the dashboard's built-in
feed instead (see FEED_SOURCE in the README).

    python -m trading.data_feeder
"""
from __future__ import annotations

import asyncio
import logging

from .src.config import RedisSettings, Settings
from .src.data import redis_bus
from .src.data.websocket_client import OrderbookWebSocketClient
from .src.logging_config import configure_logging

logger = logging.getLogger("data_feeder")


class RedisDataFeeder:
    """Bridges an exchange WebSocket to the Redis order book stream."""

    def __init__(self, websocket_uri: str, redis_settings: RedisSettings):
        self.redis_settings = redis_settings
        self.redis_client = redis_bus.connect(redis_settings, label="data_feeder")
        self.websocket_client = OrderbookWebSocketClient(
            uri=websocket_uri,
            callback=self.handle_orderbook_update,
        )

    def handle_orderbook_update(self, data: dict) -> None:
        if self.redis_client is None:
            # Reconnect lazily so a Redis restart does not require a feeder restart.
            self.redis_client = redis_bus.connect(self.redis_settings, label="data_feeder")

        if not redis_bus.publish_orderbook(self.redis_client, data):
            self.redis_client = None

    async def start(self) -> None:
        logger.info("Starting crypto order book feeder")
        await self.websocket_client.connect()


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    feeder = RedisDataFeeder(
        websocket_uri=settings.feed.websocket_uri,
        redis_settings=settings.redis,
    )
    try:
        asyncio.run(feeder.start())
    except KeyboardInterrupt:
        logger.info("Feeder stopped by user")


if __name__ == "__main__":
    main()
