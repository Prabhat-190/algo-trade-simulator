"""Tests for the thread-safe market state wrapper."""
from __future__ import annotations

import threading

import pytest

from trading.src.models.simulator import TradeSimulator
from trading.src.services.market_state import MarketState
from trading.tests.conftest import EXPECTED_MID_PRICE


def test_snapshot_before_any_data():
    state = MarketState(TradeSimulator())
    snapshot = state.snapshot()

    assert snapshot["mid_price"] is None
    assert snapshot["spread"] is None
    assert snapshot["imbalance"] is None
    assert state.last_update_time == 0
    assert state.price_history() == []


def test_snapshot_reflects_applied_frame(market):
    snapshot = market.snapshot()

    assert snapshot["symbol"] == "BTC-USDT-SWAP"
    assert snapshot["mid_price"] == pytest.approx(EXPECTED_MID_PRICE)
    assert snapshot["spread"] == pytest.approx(1.0)
    assert snapshot["spread_pct"] == pytest.approx(1.0 / EXPECTED_MID_PRICE * 100)
    assert snapshot["depth"] > 0


def test_apply_frame_records_price_history(sample_orderbook):
    state = MarketState(TradeSimulator())
    state.apply_frame(sample_orderbook)
    state.apply_frame(sample_orderbook)

    history = state.price_history()
    assert len(history) == 2
    assert all(price == pytest.approx(EXPECTED_MID_PRICE) for _, price in history)


def test_price_history_is_bounded(sample_orderbook):
    state = MarketState(TradeSimulator(), history_size=5)
    for _ in range(20):
        state.apply_frame(sample_orderbook)

    assert len(state.price_history()) == 5


def test_malformed_frame_is_rejected_without_raising():
    state = MarketState(TradeSimulator())
    state.apply_frame({"asks": [["not-a-number", "1.0"]], "bids": []})

    assert state.snapshot()["mid_price"] is None
    assert state.price_history() == []


def test_simulate_market_order_passes_through(market):
    result = market.simulate_market_order(
        side="buy", quantity=0.01, exchange="OKX",
        market_type="spot", fee_tier="VIP0", volatility=0.01,
    )
    assert result["net_cost"] > 0


def test_orderbook_frames_returns_dataframes(market):
    asks_df, bids_df = market.orderbook_frames()
    assert not asks_df.empty
    assert not bids_df.empty


def test_concurrent_writes_and_reads_stay_consistent(sample_orderbook):
    state = MarketState(TradeSimulator())
    state.apply_frame(sample_orderbook)
    errors: list[Exception] = []
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            state.apply_frame(sample_orderbook)

    def reader():
        try:
            while not stop.is_set():
                snapshot = state.snapshot()
                if snapshot["mid_price"] is not None:
                    assert snapshot["mid_price"] == pytest.approx(EXPECTED_MID_PRICE)
                state.orderbook_frames()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for thread in threads:
        thread.start()
    threading.Event().wait(0.5)
    stop.set()
    for thread in threads:
        thread.join(timeout=5)

    assert errors == []
