"""Tests for the stock quote feeder's synthetic book construction."""
from __future__ import annotations

import pytest

from trading.src.config import StockFeedSettings
from trading.stock_data_feeder import DEPTH_LEVELS, MAX_SPREAD_PCT, StockQuoteFeeder


@pytest.fixture
def feeder() -> StockQuoteFeeder:
    """A feeder built without touching Redis or the network."""
    instance = StockQuoteFeeder.__new__(StockQuoteFeeder)
    instance.settings = StockFeedSettings(symbol="AAPL", provider="finnhub")
    instance.symbol = "AAPL"
    instance.provider = "finnhub"
    instance.redis_client = None
    return instance


def test_build_synthetic_orderbook_shape(feeder):
    orderbook = feeder.build_synthetic_orderbook({"price": 200.0, "previous_close": 198.0})

    assert orderbook["symbol"] == "AAPL"
    assert orderbook["asset_class"] == "stock"
    assert orderbook["exchange"] == "FINNHUB"
    assert len(orderbook["asks"]) == DEPTH_LEVELS
    assert len(orderbook["bids"]) == DEPTH_LEVELS


def test_book_brackets_the_quote_price(feeder):
    orderbook = feeder.build_synthetic_orderbook({"price": 200.0, "previous_close": 198.0})

    assert orderbook["asks"][0][0] > 200.0
    assert orderbook["bids"][0][0] < 200.0
    assert orderbook["asks"][0][0] > orderbook["bids"][0][0]


def test_levels_are_monotonic_with_growing_size(feeder):
    orderbook = feeder.build_synthetic_orderbook({"price": 200.0, "previous_close": 200.0})

    ask_prices = [price for price, _ in orderbook["asks"]]
    ask_sizes = [size for _, size in orderbook["asks"]]
    assert ask_prices == sorted(ask_prices)
    assert ask_sizes == sorted(ask_sizes)


def test_large_move_is_capped_at_max_spread(feeder):
    # A doubling overnight would imply an enormous spread without the cap.
    orderbook = feeder.build_synthetic_orderbook({"price": 400.0, "previous_close": 200.0})
    spread = orderbook["asks"][0][0] - orderbook["bids"][0][0]

    assert spread / 400.0 <= MAX_SPREAD_PCT * 2


def test_missing_previous_close_is_tolerated(feeder):
    orderbook = feeder.build_synthetic_orderbook({"price": 200.0})
    assert orderbook["asks"][0][0] > 200.0


def test_unsupported_provider_raises(feeder):
    feeder.provider = "carrier-pigeon"
    with pytest.raises(ValueError, match="Unsupported stock provider"):
        feeder.fetch_quote()


def test_missing_api_key_raises(feeder):
    feeder.settings = StockFeedSettings(symbol="AAPL", provider="finnhub", api_key="")
    with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
        feeder.fetch_quote()
