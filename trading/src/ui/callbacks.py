"""Dash callback registration.

Each callback is a small module-level function so the formatting logic can be
tested without spinning up a Dash server.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import dash
from dash import Input, Output, State, html

from ..models.trading_project import TradingProject, TradingProjectStore
from ..services.market_state import MarketState
from . import figures
from .layout import METRIC_FIELDS

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
CONNECTED_WITHIN_SECONDS = 6.0

PROJECT_FIELD_ORDER = (
    "name", "strategy", "exchange", "market_type",
    "symbol", "side", "quantity_usd", "volatility", "fee_tier",
)

HISTORY_COLUMNS = [
    ("time", "Time"),
    ("symbol", "Symbol"),
    ("side", "Side"),
    ("quantity_usd", "Size (USD)"),
    ("net_cost", "Net Cost"),
    ("net_cost_pct", "Net Cost %"),
]


def format_currency(value: float) -> str:
    return f"${value:,.4f}"


def format_metrics(result: dict[str, Any], project_name: str, symbol: str,
                   strategy: str, quantity: float, side: str) -> list[str]:
    """Turn a simulation result into the seven result-panel strings."""
    strategy_label = (strategy or "market_order").replace("_", " ").title()
    return [
        f"{project_name or 'Untitled Project'} | {strategy_label} | {symbol} | "
        f"{side.upper()} ${quantity:,.2f}",
        f"{format_currency(result['slippage'])} ({result['slippage_percentage']:.4f}%)",
        f"{format_currency(result['fees']['total_fee'])} "
        f"({result['fees']['effective_rate'] * 100:.4f}%)",
        f"{format_currency(result['market_impact']['total_impact'])} "
        f"({result['market_impact_percentage']:.4f}%)",
        f"{format_currency(result['net_cost'])} ({result['net_cost_percentage']:.4f}%)",
        f"Maker: {result['maker_proportion'] * 100:.2f}% / "
        f"Taker: {(1 - result['maker_proportion']) * 100:.2f}%",
        f"{result['processing_time']:.2f} ms",
    ]


def describe_connection(last_update: float, now: float | None = None) -> tuple[str, str]:
    """Return (status text, last update text) for the connection panel."""
    if not last_update:
        return "Waiting for data", "--"

    now = now if now is not None else time.time()
    age = now - last_update
    status = "Connected" if age < CONNECTED_WITHIN_SECONDS else f"Stale ({age:.0f}s ago)"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_update))
    return status, stamp


def build_history_table(rows: list[dict[str, Any]]) -> Any:
    """Render simulation history rows as a table, newest first."""
    if not rows:
        return html.P("Run a simulation to start building history.", className="text-muted")

    return html.Table([
        html.Thead(html.Tr([html.Th(label) for _, label in HISTORY_COLUMNS])),
        html.Tbody([
            html.Tr([html.Td(row.get(key, "--")) for key, _ in HISTORY_COLUMNS])
            for row in reversed(rows)
        ]),
    ], className="history-table")


def register_callbacks(
    app: dash.Dash,
    market: MarketState,
    project_store: TradingProjectStore | None = None,
    feed_status: Callable[[], dict[str, Any]] | None = None,
) -> None:
    """Attach every dashboard callback to ``app``."""
    metric_outputs = [Output(field_id, "children") for field_id, _ in METRIC_FIELDS]

    @app.callback(
        [
            Output("saved-project-dropdown", "options"),
            Output("saved-project-dropdown", "value"),
            Output("project-status", "children"),
        ],
        Input("save-project-button", "n_clicks"),
        [
            State("project-name-input", "value"),
            State("strategy-dropdown", "value"),
            State("exchange-dropdown", "value"),
            State("market-type-dropdown", "value"),
            State("symbol-input", "value"),
            State("side-dropdown", "value"),
            State("quantity-input", "value"),
            State("volatility-slider", "value"),
            State("fee-tier-dropdown", "value"),
        ],
        prevent_initial_call=True,
    )
    def save_project(_clicks, *values):
        if project_store is None:
            return [], None, "Project store is not configured."

        project = TradingProject.from_dict(dict(zip(PROJECT_FIELD_ORDER, values, strict=True)))
        project_store.save(project)
        return project_store.list_projects(), project.name, f"Saved project: {project.name}"

    @app.callback(
        [
            Output("project-name-input", "value"),
            Output("strategy-dropdown", "value"),
            Output("exchange-dropdown", "value"),
            Output("market-type-dropdown", "value"),
            Output("symbol-input", "value"),
            Output("side-dropdown", "value"),
            Output("quantity-input", "value"),
            Output("volatility-slider", "value"),
            Output("fee-tier-dropdown", "value"),
        ],
        Input("saved-project-dropdown", "value"),
    )
    def load_project(project_name):
        if project_store is None or not project_name:
            raise dash.exceptions.PreventUpdate

        project = project_store.get(project_name)
        if project is None:
            raise dash.exceptions.PreventUpdate

        return tuple(getattr(project, field) for field in PROJECT_FIELD_ORDER)

    @app.callback(
        metric_outputs + [
            Output("cost-breakdown-graph", "figure"),
            Output("simulation-history", "data"),
        ],
        Input("simulate-button", "n_clicks"),
        [
            State("project-name-input", "value"),
            State("strategy-dropdown", "value"),
            State("exchange-dropdown", "value"),
            State("market-type-dropdown", "value"),
            State("symbol-input", "value"),
            State("side-dropdown", "value"),
            State("quantity-input", "value"),
            State("volatility-slider", "value"),
            State("fee-tier-dropdown", "value"),
            State("simulation-history", "data"),
        ],
        prevent_initial_call=True,
    )
    def simulate_order(_clicks, project_name, strategy, exchange, market_type,
                       symbol, side, quantity, volatility, fee_tier, history):
        history = history or []
        snapshot = market.snapshot()
        mid_price = snapshot["mid_price"]

        if not mid_price:
            message = "Waiting for market data"
            return [message] * len(METRIC_FIELDS) + [figures.placeholder(message), history]

        if not quantity or quantity <= 0:
            message = "Enter a quantity greater than zero"
            return [message] * len(METRIC_FIELDS) + [figures.placeholder(message), history]

        result = market.simulate_market_order(
            side=side,
            quantity=quantity / mid_price,
            exchange=exchange,
            market_type=market_type,
            fee_tier=fee_tier,
            volatility=volatility,
        )

        if "error" in result:
            return ([result["error"]] * len(METRIC_FIELDS)
                    + [figures.placeholder(result["error"]), history])

        metrics = format_metrics(result, project_name, symbol, strategy, quantity, side)
        history = history + [{
            "time": time.strftime("%H:%M:%S"),
            "symbol": symbol,
            "side": side.upper(),
            "quantity_usd": f"${quantity:,.2f}",
            "net_cost": format_currency(result["net_cost"]),
            "net_cost_pct": f"{result['net_cost_percentage']:.4f}%",
        }][-HISTORY_LIMIT:]

        return metrics + [figures.cost_breakdown_chart(result), history]

    @app.callback(
        Output("history-table", "children"),
        Input("simulation-history", "data"),
    )
    def render_history(rows):
        return build_history_table(rows or [])

    @app.callback(
        [
            Output("ticker-mid-price", "children"),
            Output("ticker-spread", "children"),
            Output("ticker-imbalance", "children"),
            Output("ticker-depth", "children"),
            Output("orderbook-graph", "figure"),
            Output("price-history-graph", "figure"),
            Output("connection-status", "children"),
            Output("last-update-time", "children"),
            Output("feed-source-status", "children"),
            Output("feed-badge", "children"),
        ],
        Input("interval-component", "n_intervals"),
    )
    def refresh_live_panels(_n_intervals):
        snapshot = market.snapshot()
        asks_df, bids_df = market.orderbook_frames()
        status, stamp = describe_connection(snapshot["last_update"] or 0)

        mid_price = snapshot["mid_price"]
        spread = snapshot["spread"]
        imbalance = snapshot["imbalance"]
        depth = snapshot["depth"]

        source = "starting…"
        if feed_status is not None:
            info = feed_status()
            active = info.get("active_source", "none")
            configured = info.get("configured_source", "auto")
            frames = info.get("frames_received", 0)
            source = (f"{active} ({frames} frames)" if active != "none"
                      else f"{configured}: no frames yet")

        return (
            f"${mid_price:,.2f}" if mid_price else "--",
            f"{spread:,.2f} ({snapshot['spread_pct']:.3f}%)" if spread and snapshot["spread_pct"] else "--",
            f"{imbalance:+.3f}" if imbalance is not None else "--",
            f"{depth:,.2f}" if depth else "--",
            figures.depth_chart(asks_df, bids_df),
            figures.price_history_chart(market.price_history()),
            status,
            stamp,
            source,
            f"{snapshot['symbol'] or 'no symbol'} · {status.lower()}",
        )
