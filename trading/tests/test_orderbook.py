"""Tests for the order book data structure."""
from __future__ import annotations

import pytest

from trading.src.data.orderbook import Orderbook
from trading.tests.conftest import BEST_ASK, BEST_BID, EXPECTED_MID_PRICE

TOTAL_BID_VOLUME = 1.0 + 2.0 + 3.0 + 4.0 + 5.0
TOTAL_ASK_VOLUME = 1.5 + 2.0 + 3.0 + 4.0 + 5.0


@pytest.fixture
def book(sample_orderbook) -> Orderbook:
    orderbook = Orderbook()
    orderbook.update(sample_orderbook)
    return orderbook


def test_empty_book_returns_none():
    orderbook = Orderbook()
    assert orderbook.get_mid_price() is None
    assert orderbook.get_spread() is None
    assert orderbook.get_spread_percentage() is None
    assert orderbook.get_orderbook_imbalance() is None


def test_mid_price_and_spread(book):
    assert book.get_mid_price() == pytest.approx(EXPECTED_MID_PRICE)
    assert book.get_spread() == pytest.approx(BEST_ASK - BEST_BID)
    assert book.get_spread_percentage() == pytest.approx(
        (BEST_ASK - BEST_BID) / EXPECTED_MID_PRICE * 100)


def test_levels_are_sorted_best_first(book):
    assert book.asks[0][0] == BEST_ASK
    assert book.bids[0][0] == BEST_BID
    assert book.asks == sorted(book.asks)
    assert book.bids == sorted(book.bids, reverse=True)


def test_volume_lookups(book):
    assert book.get_volume_at_price("ask", BEST_ASK) == pytest.approx(1.5)
    assert book.get_volume_at_price("bid", BEST_BID) == pytest.approx(1.0)
    assert book.get_volume_at_price("ask", 1.0) == 0.0

    assert book.get_volume_up_to_price("ask", 45002.0) == pytest.approx(1.5 + 2.0 + 3.0)
    assert book.get_volume_up_to_price("bid", 44998.0) == pytest.approx(1.0 + 2.0 + 3.0)


def test_price_for_volume(book):
    assert book.get_price_for_volume("ask", 2.0) == pytest.approx(45001.0)
    assert book.get_price_for_volume("bid", 2.0) == pytest.approx(44999.0)
    # More volume than the book holds cannot be filled.
    assert book.get_price_for_volume("ask", 1_000_000) is None


def test_imbalance(book):
    expected = (TOTAL_BID_VOLUME - TOTAL_ASK_VOLUME) / (TOTAL_BID_VOLUME + TOTAL_ASK_VOLUME)
    assert book.get_orderbook_imbalance() == pytest.approx(expected)


def test_max_depth_truncates_levels(sample_orderbook):
    orderbook = Orderbook(max_depth=2)
    orderbook.update(sample_orderbook)
    assert len(orderbook.asks) == 2
    assert len(orderbook.bids) == 2


def test_to_dataframe_adds_cumulative_quantity(book):
    asks_df, bids_df = book.to_dataframe()

    assert list(asks_df.columns) == ["price", "quantity", "cumulative_quantity"]
    assert asks_df["cumulative_quantity"].iloc[-1] == pytest.approx(TOTAL_ASK_VOLUME)
    assert bids_df["cumulative_quantity"].iloc[-1] == pytest.approx(TOTAL_BID_VOLUME)


def test_to_dataframe_on_empty_book():
    asks_df, bids_df = Orderbook().to_dataframe()
    assert asks_df.empty
    assert bids_df.empty
