"""Tests for the trade simulator's cost estimation."""
from __future__ import annotations

import pytest

from trading.tests.conftest import EXPECTED_MID_PRICE

RESULT_KEYS = (
    "timestamp", "exchange", "symbol", "side", "quantity",
    "mid_price", "execution_price", "order_value",
    "maker_proportion", "fees", "slippage", "slippage_percentage",
    "market_impact", "market_impact_percentage",
    "net_cost", "net_cost_percentage", "processing_time",
)


def test_update_orderbook_populates_book(simulator, sample_orderbook):
    processing_time = simulator.update_orderbook(sample_orderbook)

    assert simulator.orderbook.exchange == "OKX"
    assert simulator.orderbook.symbol == "BTC-USDT-SWAP"
    assert len(simulator.orderbook.asks) == 5
    assert len(simulator.orderbook.bids) == 5
    assert processing_time > 0


def test_simulate_market_order_returns_all_fields(loaded_simulator):
    result = loaded_simulator.simulate_market_order(side="buy", quantity=0.1)

    for key in RESULT_KEYS:
        assert key in result

    assert result["side"] == "buy"
    assert result["quantity"] == 0.1
    assert result["mid_price"] == pytest.approx(EXPECTED_MID_PRICE)
    assert result["order_value"] == pytest.approx(0.1 * EXPECTED_MID_PRICE)


def test_net_cost_is_sum_of_components(loaded_simulator):
    result = loaded_simulator.simulate_market_order(side="buy", quantity=0.1)

    expected = (
        result["fees"]["total_fee"]
        + result["slippage"]
        + result["market_impact"]["total_impact"]
    )
    assert result["net_cost"] == pytest.approx(expected)
    assert result["fees"]["total_fee"] > 0
    assert result["slippage"] >= 0
    assert result["market_impact"]["total_impact"] > 0


def test_empty_orderbook_reports_error(simulator):
    assert simulator.simulate_market_order(side="buy", quantity=1.0)["error"] == "Orderbook is empty"


@pytest.mark.parametrize("quantity", [0, -1, None])
def test_non_positive_quantity_rejected(loaded_simulator, quantity):
    result = loaded_simulator.simulate_market_order(side="buy", quantity=quantity)
    assert result == {"error": "Quantity must be greater than zero"}


def test_unknown_side_rejected(loaded_simulator):
    result = loaded_simulator.simulate_market_order(side="hodl", quantity=1.0)
    assert "Unknown order side" in result["error"]


def test_cost_grows_with_order_size(loaded_simulator):
    small = loaded_simulator.simulate_market_order(side="buy", quantity=0.001)
    large = loaded_simulator.simulate_market_order(side="buy", quantity=1.0)

    assert large["slippage"] > small["slippage"]
    assert large["market_impact"]["total_impact"] > small["market_impact"]["total_impact"]
    assert large["net_cost_percentage"] > small["net_cost_percentage"]


def test_small_order_cost_is_dominated_by_fees(loaded_simulator):
    result = loaded_simulator.simulate_market_order(side="buy", quantity=0.0001)

    assert result["net_cost_percentage"] < 0.5
    assert result["fees"]["total_fee"] > result["market_impact"]["total_impact"]


def test_anomalous_book_is_flagged(simulator):
    simulator.update_orderbook({
        "timestamp": "now", "exchange": "OKX", "symbol": "X",
        "asks": [["100.0", "0.0001"]],
        "bids": [["99.0", "1000.0"]],
    })
    result = simulator.simulate_market_order(side="buy", quantity=0.1)
    assert result["anomaly_flag"] is True


def test_average_processing_time_tracks_updates(simulator, sample_orderbook):
    assert simulator.get_average_processing_time() == 0
    simulator.update_orderbook(sample_orderbook)
    assert simulator.get_average_processing_time() > 0
