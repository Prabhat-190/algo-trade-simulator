"""Stock quote feeder.

Free stock quote APIs do not expose exchange order book depth, so this service
polls a quote endpoint and expands the last price into a synthetic Level-2 book
that the existing cost models can consume.

    python -m trading.stock_data_feeder --symbol AAPL
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from dataclasses import replace

from .src.config import RedisSettings, Settings, StockFeedSettings
from .src.data import redis_bus
from .src.logging_config import configure_logging

logger = logging.getLogger("stock_data_feeder")

DEPTH_LEVELS = 10
BASE_LEVEL_SIZE = 100
MIN_SPREAD_PCT = 0.0005
MAX_SPREAD_PCT = 0.01
HTTP_TIMEOUT_SECONDS = 10


class StockQuoteFeeder:
    """Polls a quote provider and publishes synthetic order book frames."""

    def __init__(self, feed_settings: StockFeedSettings, redis_settings: RedisSettings):
        self.settings = feed_settings
        self.symbol = feed_settings.symbol
        self.provider = feed_settings.provider
        self.redis_settings = redis_settings
        self.redis_client = redis_bus.connect(redis_settings, label="stock_feeder")

    # -- quote providers ---------------------------------------------------

    def fetch_quote(self) -> dict[str, float]:
        if self.provider == "finnhub":
            return self._fetch_finnhub_quote()
        if self.provider == "alphavantage":
            return self._fetch_alpha_vantage_quote()
        raise ValueError(f"Unsupported stock provider: {self.provider}")

    def _get_json(self, url: str) -> dict:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fetch_finnhub_quote(self) -> dict[str, float]:
        if not self.settings.api_key:
            raise ValueError("FINNHUB_API_KEY is required for provider=finnhub")

        params = urllib.parse.urlencode({"symbol": self.symbol, "token": self.settings.api_key})
        payload = self._get_json(f"https://finnhub.io/api/v1/quote?{params}")

        price = float(payload.get("c") or 0)
        if price <= 0:
            raise ValueError(f"Finnhub returned no price for {self.symbol}: {payload}")
        return {"price": price, "previous_close": float(payload.get("pc") or price)}

    def _fetch_alpha_vantage_quote(self) -> dict[str, float]:
        if not self.settings.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required for provider=alphavantage")

        params = urllib.parse.urlencode({
            "function": "GLOBAL_QUOTE",
            "symbol": self.symbol,
            "apikey": self.settings.api_key,
        })
        payload = self._get_json(f"https://www.alphavantage.co/query?{params}")

        quote = payload.get("Global Quote", {})
        price = float(quote.get("05. price") or 0)
        if price <= 0:
            raise ValueError(f"Alpha Vantage returned no price for {self.symbol}: {payload}")
        return {"price": price, "previous_close": float(quote.get("08. previous close") or price)}

    # -- synthetic book ----------------------------------------------------

    def build_synthetic_orderbook(self, quote: dict[str, float]) -> dict:
        price = quote["price"]
        previous_close = quote.get("previous_close") or price
        move = abs(price - previous_close) / previous_close if previous_close else 0
        spread_pct = max(MIN_SPREAD_PCT, min(MAX_SPREAD_PCT, move / 10 or 0.001))

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exchange": self.provider.upper(),
            "symbol": self.symbol,
            "asset_class": "stock",
            "source": f"{self.provider} quote expanded into a synthetic order book",
            "asks": self._levels(price, spread_pct, direction=1),
            "bids": self._levels(price, spread_pct, direction=-1),
        }

    @staticmethod
    def _levels(price: float, spread_pct: float, direction: int) -> list[list[float]]:
        half_spread = spread_pct / 2
        levels = []
        for index in range(1, DEPTH_LEVELS + 1):
            level_price = price * (1 + direction * (half_spread + index * spread_pct / 3))
            levels.append([round(level_price, 4), float(BASE_LEVEL_SIZE * index)])
        return levels

    # -- loop --------------------------------------------------------------

    def publish(self, orderbook: dict) -> None:
        if self.redis_client is None:
            self.redis_client = redis_bus.connect(self.redis_settings, label="stock_feeder")

        if redis_bus.publish_orderbook(self.redis_client, orderbook):
            logger.info("Published %s at %.4f", self.symbol, orderbook["asks"][0][0])
        else:
            self.redis_client = None

    def start(self) -> None:
        logger.info("Polling %s every %ss via %s",
                    self.symbol, self.settings.poll_interval, self.provider)
        while True:
            try:
                self.publish(self.build_synthetic_orderbook(self.fetch_quote()))
            except Exception as exc:
                logger.error("Unable to publish %s quote: %s", self.symbol, exc)
            time.sleep(self.settings.poll_interval)


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    defaults = StockFeedSettings.from_env()

    parser = argparse.ArgumentParser(
        description="Poll stock quotes and publish simulator-compatible order book frames.")
    parser.add_argument("--symbol", default=defaults.symbol)
    parser.add_argument("--provider", default=defaults.provider,
                        choices=["finnhub", "alphavantage"])
    parser.add_argument("--poll-interval", type=int, default=defaults.poll_interval)
    args = parser.parse_args()

    # The API key depends on the provider, so re-resolve it in case --provider
    # differs from what the environment implied.
    key_var = "FINNHUB_API_KEY" if args.provider == "finnhub" else "ALPHA_VANTAGE_API_KEY"
    feed_settings = replace(
        defaults,
        symbol=args.symbol.upper(),
        provider=args.provider,
        poll_interval=args.poll_interval,
        api_key=os.environ.get(key_var, ""),
    )

    StockQuoteFeeder(feed_settings, settings.redis).start()


if __name__ == "__main__":
    main()
