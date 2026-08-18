"""Tests for callback formatting helpers and layout wiring."""
from __future__ import annotations

import time

from dash import html

from trading.src.ui import figures, layout
from trading.src.ui.callbacks import (
    CONNECTED_WITHIN_SECONDS,
    build_history_table,
    describe_connection,
    format_currency,
    format_metrics,
)

SAMPLE_RESULT = {
    "slippage": 1.2345,
    "slippage_percentage": 0.0123,
    "fees": {"total_fee": 0.5, "effective_rate": 0.0008},
    "market_impact": {"total_impact": 2.0},
    "market_impact_percentage": 0.02,
    "net_cost": 3.7345,
    "net_cost_percentage": 0.0373,
    "maker_proportion": 0.6,
    "processing_time": 1.5,
}


def test_format_currency():
    assert format_currency(1234.5) == "$1,234.5000"


def test_format_metrics_returns_one_string_per_field():
    metrics = format_metrics(SAMPLE_RESULT, "My Project", "BTC-USDT", "scalping", 100.0, "buy")

    assert len(metrics) == len(layout.METRIC_FIELDS)
    assert all(isinstance(item, str) for item in metrics)
    assert "My Project" in metrics[0]
    assert "Scalping" in metrics[0]
    assert "BUY $100.00" in metrics[0]
    assert "Maker: 60.00%" in metrics[5]
    assert "Taker: 40.00%" in metrics[5]
    assert metrics[6] == "1.50 ms"


def test_format_metrics_handles_missing_project_name():
    metrics = format_metrics(SAMPLE_RESULT, "", "BTC-USDT", "swing", 50.0, "sell")
    assert "Untitled Project" in metrics[0]


def test_describe_connection_without_data():
    assert describe_connection(0) == ("Waiting for data", "--")


def test_describe_connection_when_fresh():
    now = time.time()
    status, stamp = describe_connection(now, now=now)

    assert status == "Connected"
    assert stamp != "--"


def test_describe_connection_when_stale():
    now = time.time()
    status, _ = describe_connection(now - CONNECTED_WITHIN_SECONDS - 30, now=now)
    assert status.startswith("Stale")


def test_history_table_empty_state():
    rendered = build_history_table([])
    assert isinstance(rendered, html.P)


def test_history_table_lists_newest_first():
    rows = [
        {"time": "10:00:00", "symbol": "BTC-USDT", "side": "BUY",
         "quantity_usd": "$100.00", "net_cost": "$0.13", "net_cost_pct": "0.1300%"},
        {"time": "10:00:05", "symbol": "ETH-USDT", "side": "SELL",
         "quantity_usd": "$200.00", "net_cost": "$0.26", "net_cost_pct": "0.1300%"},
    ]
    table = build_history_table(rows)
    body = table.children[1]

    assert len(body.children) == 2
    assert body.children[0].children[0].children == "10:00:05"


def test_layout_defines_every_metric_and_ticker_id():
    built = layout.build_layout(
        project_options=[{"label": "Demo", "value": "Demo"}],
        exchange_options=[{"label": "OKX", "value": "OKX"}],
        default_symbol="BTC-USDT",
    )

    ids = set()

    def walk(node):
        component_id = getattr(node, "id", None)
        if isinstance(component_id, str):
            ids.add(component_id)
        children = getattr(node, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                walk(child)
        elif children is not None:
            walk(children)

    walk(built)

    for field_id, _ in layout.METRIC_FIELDS:
        assert field_id in ids
    for field_id, _ in layout.TICKER_FIELDS:
        assert field_id in ids
    assert {"simulate-button", "orderbook-graph", "price-history-graph",
            "cost-breakdown-graph", "simulation-history", "interval-component"} <= ids


def test_placeholder_figure_carries_message():
    fig = figures.placeholder("Waiting for order book data")
    assert fig.layout.annotations[0].text == "Waiting for order book data"


def test_depth_chart_falls_back_when_empty():
    import pandas as pd
    empty = pd.DataFrame(columns=["price", "quantity", "cumulative_quantity"])
    fig = figures.depth_chart(empty, empty)
    assert fig.layout.annotations


def test_cost_breakdown_chart_has_three_slices():
    fig = figures.cost_breakdown_chart(SAMPLE_RESULT)
    assert list(fig.data[0].labels) == ["Fees", "Slippage", "Market Impact"]


def test_cost_breakdown_chart_handles_all_zero_costs():
    zeroed = {
        **SAMPLE_RESULT,
        "slippage": 0,
        "fees": {"total_fee": 0, "effective_rate": 0},
        "market_impact": {"total_impact": 0},
    }
    assert figures.cost_breakdown_chart(zeroed).layout.annotations


def test_price_history_chart_needs_two_points():
    assert figures.price_history_chart([(1.0, 100.0)]).layout.annotations
    assert figures.price_history_chart([(1.0, 100.0), (2.0, 101.0)]).data
