"""
Stock data feeder.

This service polls a free stock quote API and converts the latest quote into a
synthetic Level-2 style order book so the existing simulator can run on stocks.
Free stock quote APIs usually do not provide full exchange order-book depth.
"""
import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Dict, List

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StockDataFeeder")


class StockQuoteFeeder:
    def __init__(
        self,
        symbol: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        provider: str = "finnhub",
        api_key: str = "",
        poll_interval: int = 15,
    ):
        self.symbol = symbol.upper()
        self.provider = provider.lower()
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client: redis.Redis | None = None
        self._redis_connected = False
        
        # Initialize Redis connection
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection with retry logic."""
        max_retries = 5
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Redis at {self.redis_host}:{self.redis_port} (attempt {attempt + 1}/{max_retries})")
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                # Test the connection
                self.redis_client.ping()
                self._redis_connected = True
                logger.info("Successfully connected to Redis")
                return
            except (RedisConnectionError, RedisError, TimeoutError) as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to Redis after {max_retries} attempts. Running without Redis.")
                    self.redis_client = None
                    self._redis_connected = False

    def fetch_quote(self) -> Dict:
        if self.provider == "finnhub":
            return self._fetch_finnhub_quote()
        if self.provider == "alphavantage":
            return self._fetch_alpha_vantage_quote()
        raise ValueError(f"Unsupported stock provider: {self.provider}")

    def _fetch_finnhub_quote(self) -> Dict:
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY is required for provider=finnhub")
        params = urllib.parse.urlencode({"symbol": self.symbol, "token": self.api_key})
        url = f"https://finnhub.io/api/v1/quote?{params}"
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        price = float(payload.get("c") or 0)
        previous_close = float(payload.get("pc") or price)
        if price <= 0:
            raise ValueError(f"Finnhub returned no current price for {self.symbol}: {payload}")
        return {"price": price, "previous_close": previous_close}

    def _fetch_alpha_vantage_quote(self) -> Dict:
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required for provider=alphavantage")
        params = urllib.parse.urlencode({
            "function": "GLOBAL_QUOTE",
            "symbol": self.symbol,
            "apikey": self.api_key,
        })
        url = f"https://www.alphavantage.co/query?{params}"
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        quote = payload.get("Global Quote", {})
        price = float(quote.get("05. price") or 0)
        previous_close = float(quote.get("08. previous close") or price)
        if price <= 0:
            raise ValueError(f"Alpha Vantage returned no current price for {self.symbol}: {payload}")
        return {"price": price, "previous_close": previous_close}

    def build_synthetic_orderbook(self, quote: Dict) -> Dict:
        price = quote["price"]
        previous_close = quote.get("previous_close") or price
        move = abs(price - previous_close) / previous_close if previous_close else 0
        spread_pct = max(0.0005, min(0.01, move / 10 or 0.001))
        base_size = 100

        asks = self._levels(price, spread_pct, base_size, side="ask")
        bids = self._levels(price, spread_pct, base_size, side="bid")
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exchange": self.provider.upper(),
            "symbol": self.symbol,
            "asset_class": "stock",
            "source": f"{self.provider} quote converted to synthetic orderbook",
            "asks": asks,
            "bids": bids,
        }

    @staticmethod
    def _levels(price: float, spread_pct: float, base_size: int, side: str) -> List[List[float]]:
        levels = []
        direction = 1 if side == "ask" else -1
        half_spread = spread_pct / 2
        for index in range(1, 11):
            level_price = price * (1 + direction * (half_spread + index * spread_pct / 3))
            level_qty = base_size * index
            levels.append([round(level_price, 4), float(level_qty)])
        return levels

    def publish(self, orderbook: Dict) -> None:
        if not self._redis_connected or not self.redis_client:
            logger.warning("Redis not connected, skipping orderbook publish")
            return
            
        try:
            payload = json.dumps(orderbook)
            channel = f"orderbook:{self.symbol}:stream"
            self.redis_client.publish(channel, payload)
            self.redis_client.set(f"orderbook:{self.symbol}:latest", payload)
            logger.info("Published %s stock quote as synthetic orderbook at %.4f", self.symbol, orderbook["asks"][0][0])
        except (RedisConnectionError, RedisError, TimeoutError) as e:
            logger.error(f"Redis error publishing data: {e}. Attempting to reconnect...")
            self._init_redis()
        except Exception as exc:
            logger.error("Unable to publish stock quote: %s", exc)

    def start(self) -> None:
        logger.info("Starting stock quote feeder for %s using %s", self.symbol, self.provider)
        while True:
            try:
                quote = self.fetch_quote()
                self.publish(self.build_synthetic_orderbook(quote))
            except Exception as exc:
                logger.error("Unable to publish stock quote: %s", exc)
            time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Poll stock quotes and publish simulator-compatible orderbook frames.")
    parser.add_argument("--symbol", default=os.environ.get("STOCK_SYMBOL", "AAPL"))
    parser.add_argument("--provider", default=os.environ.get("STOCK_PROVIDER", "finnhub"))
    parser.add_argument("--poll-interval", type=int, default=int(os.environ.get("STOCK_POLL_INTERVAL", 15)))
    args = parser.parse_args()

    provider = args.provider.lower()
    api_key = os.environ.get("FINNHUB_API_KEY", "") if provider == "finnhub" else os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    feeder = StockQuoteFeeder(
        symbol=args.symbol,
        redis_host=os.environ.get("REDIS_HOST", "localhost"),
        redis_port=int(os.environ.get("REDIS_PORT", 6379)),
        provider=provider,
        api_key=api_key,
        poll_interval=args.poll_interval,
    )
    feeder.start()


if __name__ == "__main__":
    main()