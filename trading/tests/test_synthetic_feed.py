"""Tests for the synthetic order book generator."""
from __future__ import annotations

import pytest

from trading.src.config import FeedSettings
from trading.src.data.orderbook import Orderbook
from trading.src.data.synthetic_feed import SyntheticOrderbookFeed


@pytest.fixture
def feed(feed_settings: FeedSettings) -> SyntheticOrderbookFeed:
    return SyntheticOrderbookFeed(feed_settings, seed=42)


def test_frame_has_live_feed_shape(feed, feed_settings):
    frame = feed.step()

    assert set(frame) >= {"timestamp", "exchange", "symbol", "asks", "bids"}
    assert frame["symbol"] == feed_settings.symbol
    assert frame["exchange"] == feed_settings.exchange
    assert len(frame["asks"]) == feed_settings.synthetic_depth
    assert len(frame["bids"]) == feed_settings.synthetic_depth


def test_book_never_crosses(feed):
    for _ in range(200):
        frame = feed.step()
        best_ask = min(price for price, _ in frame["asks"])
        best_bid = max(price for price, _ in frame["bids"])
        assert best_ask > best_bid


def test_levels_walk_away_from_the_touch(feed):
    frame = feed.step()
    ask_prices = [price for price, _ in frame["asks"]]
    bid_prices = [price for price, _ in frame["bids"]]

    assert ask_prices == sorted(ask_prices)
    assert bid_prices == sorted(bid_prices, reverse=True)
    assert all(size > 0 for _, size in frame["asks"] + frame["bids"])


def test_price_stays_positive_and_bounded(feed, feed_settings):
    for _ in range(500):
        feed.step()

    # Mean reversion keeps a long session near the configured start price.
    assert feed.mid_price > 0
    assert 0.2 < feed.mid_price / feed_settings.synthetic_start_price < 5.0


def test_seed_makes_output_reproducible(feed_settings):
    first = SyntheticOrderbookFeed(feed_settings, seed=7).step()
    second = SyntheticOrderbookFeed(feed_settings, seed=7).step()
    assert first["asks"] == second["asks"]
    assert first["bids"] == second["bids"]


def test_spread_matches_configured_basis_points(feed_settings):
    settings = FeedSettings(**{**feed_settings.__dict__, "synthetic_spread_bps": 5.0})
    feed = SyntheticOrderbookFeed(settings, seed=1)

    spreads = []
    for _ in range(300):
        frame = feed.step()
        mid = (min(p for p, _ in frame["asks"]) + max(p for p, _ in frame["bids"])) / 2
        spreads.append((min(p for p, _ in frame["asks"]) - max(p for p, _ in frame["bids"])) / mid)

    average_bps = sum(spreads) / len(spreads) * 10_000
    assert 2.0 < average_bps < 12.0


def test_frames_are_consumable_by_the_orderbook(feed):
    orderbook = Orderbook()
    orderbook.update(feed.step())

    assert orderbook.get_mid_price() > 0
    assert orderbook.get_spread() > 0
    assert -1 <= orderbook.get_orderbook_imbalance() <= 1
