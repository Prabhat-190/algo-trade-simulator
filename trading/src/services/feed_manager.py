"""
Pulls orderbook updates from redis / websocket / a local generator.
"""
import asyncio
import logging
import threading
import time
from collections.abc import Callable

import redis

from ..config import FEED_AUTO, FEED_REDIS, FEED_SYNTHETIC, FEED_WEBSOCKET, FeedSettings
from ..data import redis_bus
from ..data.synthetic_feed import SyntheticOrderbookFeed

logger = logging.getLogger(__name__)

FrameHandler = Callable[[dict], None]


class FeedManager:
    def __init__(
        self,
        settings: FeedSettings,
        on_frame: FrameHandler,
        redis_client: redis.Redis | None = None,
    ):
        self.settings = settings
        self.redis_client = redis_client
        self._on_frame = on_frame
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

        self._lock = threading.Lock()
        self._last_frame_at = 0.0
        self._frame_count = 0
        self._active_source = "none"

    def start(self) -> None:
        source = self.settings.source

        if source in (FEED_AUTO, FEED_REDIS) and self.redis_client is not None:
            self._spawn("redis-subscriber", self._run_redis_subscriber)

        if source == FEED_WEBSOCKET:
            self._spawn("websocket-feed", self._run_websocket)

        # keep a local book going so the ui isnt empty if redis/ws is quiet
        if source == FEED_SYNTHETIC:
            self._spawn("synthetic-feed", lambda: self._run_synthetic(only_when_stale=False))
        else:
            self._spawn("synthetic-fallback", lambda: self._run_synthetic(only_when_stale=True))

    def stop(self) -> None:
        self._stop.set()

    def _spawn(self, name: str, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=self._guard(name, target), name=name, daemon=True)
        thread.start()
        self._threads.append(thread)
        logger.info("Started market data thread: %s", name)

    def _guard(self, name: str, target: Callable[[], None]) -> Callable[[], None]:
        def runner() -> None:
            try:
                target()
            except Exception:
                logger.exception("Market data thread %s stopped unexpectedly", name)
        return runner

    def _run_redis_subscriber(self) -> None:
        assert self.redis_client is not None
        redis_bus.subscribe_orderbooks(
            self.redis_client,
            on_frame=lambda frame: self._emit(frame, source="redis"),
            stop_check=self._stop.is_set,
        )

    def _run_synthetic(self, only_when_stale: bool) -> None:
        feed = SyntheticOrderbookFeed(self.settings)
        interval = max(0.1, self.settings.synthetic_interval_seconds)

        while not self._stop.is_set():
            if not only_when_stale or self._fallback_should_emit():
                self._emit(feed.step(), source="synthetic")
            self._stop.wait(interval)

    def _fallback_should_emit(self) -> bool:
        with self._lock:
            active = self._active_source
            last = self._last_frame_at

        if last == 0.0 or active == "synthetic":
            return True
        return (time.time() - last) >= self.settings.stale_after_seconds

    def _run_websocket(self) -> None:
        from ..data.websocket_client import OrderbookWebSocketClient

        client = OrderbookWebSocketClient(
            uri=self.settings.websocket_uri,
            callback=lambda frame: self._emit(frame, source="websocket"),
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(client.connect())
        finally:
            loop.close()

    def _emit(self, frame: dict, source: str) -> None:
        self._on_frame(frame)
        with self._lock:
            self._last_frame_at = time.time()
            self._frame_count += 1
            self._active_source = source

    def status(self) -> dict[str, object]:
        with self._lock:
            last = self._last_frame_at
            count = self._frame_count
            active = self._active_source
        return {
            "configured_source": self.settings.source,
            "active_source": active,
            "frames_received": count,
            "last_frame_timestamp": last or None,
            "seconds_since_last_frame": (time.time() - last) if last else None,
            "threads": [t.name for t in self._threads if t.is_alive()],
        }
