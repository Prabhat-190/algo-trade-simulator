"""Environment-driven configuration for every process in the simulator."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

DEFAULT_WEBSOCKET_URI = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

# Feed sources. "auto" keeps the dashboard populated no matter how it is deployed:
# it consumes Redis when a feeder is publishing and falls back to a local source
# when nothing has arrived recently.
FEED_AUTO = "auto"
FEED_SYNTHETIC = "synthetic"
FEED_WEBSOCKET = "websocket"
FEED_REDIS = "redis"
VALID_FEED_SOURCES = (FEED_AUTO, FEED_SYNTHETIC, FEED_WEBSOCKET, FEED_REDIS)


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RedisSettings:
    """Redis connection details, resolved from either REDIS_URL or host/port pairs."""

    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    connect_timeout: float = 5.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> RedisSettings:
        # Managed Redis add-ons (Railway, Render, Upstash) expose a single URL.
        url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_PRIVATE_URL")
        if url:
            parsed = urlparse(url)
            return cls(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                db=int(parsed.path.lstrip("/") or 0),
                connect_timeout=_env_float("REDIS_CONNECT_TIMEOUT", 5.0),
                max_retries=_env_int("REDIS_MAX_RETRIES", 3),
            )
        return cls(
            host=_env_str("REDIS_HOST", "localhost"),
            port=_env_int("REDIS_PORT", 6379),
            password=os.environ.get("REDIS_PASSWORD") or None,
            db=_env_int("REDIS_DB", 0),
            connect_timeout=_env_float("REDIS_CONNECT_TIMEOUT", 5.0),
            max_retries=_env_int("REDIS_MAX_RETRIES", 3),
        )


@dataclass(frozen=True)
class FeedSettings:
    """Controls where the dashboard gets order book frames from."""

    source: str = FEED_AUTO
    websocket_uri: str = DEFAULT_WEBSOCKET_URI
    symbol: str = "BTC-USDT"
    exchange: str = "SIMULATED"
    # Seconds without a frame before the embedded fallback source takes over.
    stale_after_seconds: float = 6.0
    synthetic_interval_seconds: float = 1.0
    synthetic_start_price: float = 65000.0
    synthetic_volatility: float = 0.0009
    synthetic_depth: int = 15
    # Typical top-of-book spread in basis points (1 bp = 0.01%). Liquid crypto
    # pairs sit near 1 bp, so the default keeps cost estimates believable.
    synthetic_spread_bps: float = 1.0

    @classmethod
    def from_env(cls) -> FeedSettings:
        source = _env_str("FEED_SOURCE", FEED_AUTO).lower()
        if source not in VALID_FEED_SOURCES:
            source = FEED_AUTO
        return cls(
            source=source,
            websocket_uri=_env_str("WEBSOCKET_URI", DEFAULT_WEBSOCKET_URI),
            symbol=_env_str("SYMBOL", "BTC-USDT"),
            exchange=_env_str("EXCHANGE", "SIMULATED"),
            stale_after_seconds=_env_float("FEED_STALE_AFTER_SECONDS", 6.0),
            synthetic_interval_seconds=_env_float("SYNTHETIC_INTERVAL_SECONDS", 1.0),
            synthetic_start_price=_env_float("SYNTHETIC_START_PRICE", 65000.0),
            synthetic_volatility=_env_float("SYNTHETIC_VOLATILITY", 0.0009),
            synthetic_depth=_env_int("SYNTHETIC_DEPTH", 15),
            synthetic_spread_bps=_env_float("SYNTHETIC_SPREAD_BPS", 1.0),
        )


@dataclass(frozen=True)
class StockFeedSettings:
    """Settings for the optional stock quote feeder process."""

    symbol: str = "AAPL"
    provider: str = "finnhub"
    poll_interval: int = 15
    api_key: str = ""

    @classmethod
    def from_env(cls) -> StockFeedSettings:
        provider = _env_str("STOCK_PROVIDER", "finnhub").lower()
        key_var = "FINNHUB_API_KEY" if provider == "finnhub" else "ALPHA_VANTAGE_API_KEY"
        return cls(
            symbol=_env_str("STOCK_SYMBOL", "AAPL").upper(),
            provider=provider,
            poll_interval=_env_int("STOCK_POLL_INTERVAL", 15),
            api_key=os.environ.get(key_var, ""),
        )


@dataclass(frozen=True)
class Settings:
    """Top-level application settings."""

    host: str = "0.0.0.0"
    port: int = 8050
    debug: bool = False
    log_level: str = "INFO"
    models_dir: str | None = None
    # Health check reports market data as stale past this age.
    health_stale_after_seconds: float = 30.0
    redis: RedisSettings = field(default_factory=RedisSettings)
    feed: FeedSettings = field(default_factory=FeedSettings)

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            host=_env_str("HOST", "0.0.0.0"),
            port=_env_int("PORT", 8050),
            debug=_env_bool("DEBUG", False),
            log_level=_env_str("LOG_LEVEL", "INFO").upper(),
            models_dir=os.environ.get("MODELS_DIR") or None,
            health_stale_after_seconds=_env_float("HEALTH_STALE_AFTER_SECONDS", 30.0),
            redis=RedisSettings.from_env(),
            feed=FeedSettings.from_env(),
        )
