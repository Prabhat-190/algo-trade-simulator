"""pytest fixtures."""
from __future__ import annotations

import pytest

from trading.src.config import FeedSettings, RedisSettings, Settings
from trading.src.models.simulator import TradeSimulator
from trading.src.services.market_state import MarketState

SAMPLE_ORDERBOOK = {
    "timestamp": "2023-05-04T10:39:13Z",
    "exchange": "OKX",
    "symbol": "BTC-USDT-SWAP",
    "asks": [
        ["45000.5", "1.5"],
        ["45001.0", "2.0"],
        ["45002.0", "3.0"],
        ["45003.0", "4.0"],
        ["45004.0", "5.0"],
    ],
    "bids": [
        ["44999.5", "1.0"],
        ["44999.0", "2.0"],
        ["44998.0", "3.0"],
        ["44997.0", "4.0"],
        ["44996.0", "5.0"],
    ],
}

BEST_ASK = 45000.5
BEST_BID = 44999.5
EXPECTED_MID_PRICE = (BEST_ASK + BEST_BID) / 2


@pytest.fixture
def sample_orderbook() -> dict:
    """Five level book, mid = 45000."""
    return {
        **SAMPLE_ORDERBOOK,
        "asks": [list(level) for level in SAMPLE_ORDERBOOK["asks"]],
        "bids": [list(level) for level in SAMPLE_ORDERBOOK["bids"]],
    }


@pytest.fixture
def simulator() -> TradeSimulator:
    return TradeSimulator()


@pytest.fixture
def loaded_simulator(simulator: TradeSimulator, sample_orderbook: dict) -> TradeSimulator:
    simulator.update_orderbook(sample_orderbook)
    return simulator


@pytest.fixture
def market(loaded_simulator: TradeSimulator) -> MarketState:
    return MarketState(loaded_simulator)


@pytest.fixture
def feed_settings() -> FeedSettings:
    return FeedSettings(
        source="synthetic",
        symbol="TEST-USDT",
        exchange="TESTNET",
        synthetic_interval_seconds=0.01,
        synthetic_start_price=1000.0,
        synthetic_depth=5,
    )


@pytest.fixture
def offline_settings(feed_settings: FeedSettings) -> Settings:
    """No network. Redis retries disabled."""
    return Settings(
        port=0,
        redis=RedisSettings(host="127.0.0.1", port=1, max_retries=1, connect_timeout=0.05),
        feed=feed_settings,
    )
