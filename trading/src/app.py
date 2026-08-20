"""
Application factory for the trade simulator dashboard.
"""
import logging
import time

from flask import Flask

from .config import Settings
from .data import redis_bus
from .logging_config import configure_logging
from .models.simulator import TradeSimulator
from .models.trading_project import TradingProjectStore
from .services.feed_manager import FeedManager
from .services.market_state import MarketState
from .ui.dashboard import Dashboard

logger = logging.getLogger(__name__)


class TradeSimulatorApp:
    def __init__(self, settings: Settings | None = None, start_feeds: bool = True):
        self.settings = settings or Settings.from_env()

        self.redis_client = redis_bus.connect(self.settings.redis, label="dashboard")
        self.market = MarketState(TradeSimulator(models_dir=self.settings.models_dir))
        self.project_store = TradingProjectStore(redis_client=self.redis_client)

        self.feed_manager = FeedManager(
            settings=self.settings.feed,
            on_frame=self.market.apply_frame,
            redis_client=self.redis_client,
        )
        self.dashboard = Dashboard(
            market=self.market,
            project_store=self.project_store,
            feed_status=self.feed_manager.status,
            default_symbol=self.settings.feed.symbol,
        )

        self._register_health_route()

        if start_feeds:
            self.feed_manager.start()

    @property
    def server(self) -> Flask:
        return self.dashboard.server

    def _register_health_route(self) -> None:
        @self.server.get("/healthz")
        def healthz():
            return self.health_payload(), 200

        @self.server.get("/readyz")
        def readyz():
            payload = self.health_payload()
            ready = payload["market_data"]["status"] == "fresh"
            return {"ready": ready, **payload}, 200 if ready else 503

    def health_payload(self) -> dict:
        redis_status = "not_configured"
        redis_error = None
        if self.redis_client is not None:
            try:
                self.redis_client.ping()
                redis_status = "connected"
            except Exception as exc:
                redis_status = "error"
                redis_error = str(exc)

        last_update = self.market.last_update_time
        age = (time.time() - last_update) if last_update else None
        fresh = age is not None and age < self.settings.health_stale_after_seconds

        return {
            "status": "ok",
            "redis": {
                "status": redis_status,
                "host": self.settings.redis.host,
                "port": self.settings.redis.port,
                "error": redis_error,
            },
            "market_data": {
                "status": "fresh" if fresh else "stale",
                "last_update_timestamp": last_update or None,
                "seconds_since_update": age,
            },
            "feed": self.feed_manager.status(),
            "timestamp": time.time(),
        }

    def run(self) -> None:
        logger.info("Starting dashboard on %s:%s", self.settings.host, self.settings.port)
        self.dashboard.run(
            host=self.settings.host,
            port=self.settings.port,
            debug=self.settings.debug,
        )


def create_app(settings: Settings | None = None, start_feeds: bool = True) -> TradeSimulatorApp:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)
    return TradeSimulatorApp(settings=settings, start_feeds=start_feeds)


def create_wsgi_app(settings: Settings | None = None) -> tuple[TradeSimulatorApp, Flask]:
    app = create_app(settings)
    return app, app.server
