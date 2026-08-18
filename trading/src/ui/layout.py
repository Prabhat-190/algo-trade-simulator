"""Dashboard layout.

Pure component construction — no callbacks and no simulator access — so the
layout can be rendered and inspected in tests.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from . import figures

STRATEGY_OPTIONS = [
    {"label": "Market Order Simulation", "value": "market_order"},
    {"label": "Scalping Cost Check", "value": "scalping"},
    {"label": "Swing Trade Cost Check", "value": "swing"},
    {"label": "Large Order Impact Check", "value": "large_order"},
]

MARKET_TYPE_OPTIONS = [
    {"label": "Spot", "value": "spot"},
    {"label": "Futures", "value": "futures"},
]

SIDE_OPTIONS = [
    {"label": "Buy", "value": "buy"},
    {"label": "Sell", "value": "sell"},
]

FEE_TIER_OPTIONS = [{"label": f"VIP{tier}", "value": f"VIP{tier}"} for tier in range(6)]

VOLATILITY_MARKS = {0.001: "0.1%", 0.01: "1%", 0.02: "2%", 0.03: "3%", 0.04: "4%", 0.05: "5%"}

METRIC_FIELDS = [
    ("project-summary-output", "Project Summary"),
    ("slippage-output", "Expected Slippage"),
    ("fees-output", "Expected Fees"),
    ("market-impact-output", "Expected Market Impact"),
    ("net-cost-output", "Net Cost"),
    ("maker-taker-output", "Maker/Taker Proportion"),
    ("latency-output", "Internal Latency"),
]

TICKER_FIELDS = [
    ("ticker-mid-price", "Mid Price"),
    ("ticker-spread", "Spread"),
    ("ticker-imbalance", "Book Imbalance"),
    ("ticker-depth", "Total Depth"),
]


def _header() -> html.Div:
    return html.Div([
        html.Div([
            html.H1("Algo Trade Simulator", className="app-title"),
            html.P(
                "Real-time transaction cost analysis: slippage, fees and market impact",
                className="app-subtitle",
            ),
        ]),
        html.Div([
            html.Span(className="live-status-dot"),
            html.Span(id="feed-badge", children="starting…"),
        ], className="feed-badge"),
    ], className="app-header")


def _ticker_strip() -> dbc.Card:
    return dbc.Card(dbc.CardBody(
        dbc.Row([
            dbc.Col(html.Div([
                html.Span(label, className="ticker-label"),
                html.Span("--", id=field_id, className="ticker-value"),
            ], className="ticker-metric"), width=6, lg=3)
            for field_id, label in TICKER_FIELDS
        ])
    ), className="mb-4")


def _project_panel(project_options: list[dict[str, str]]) -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader("Trading Project"),
        dbc.CardBody([
            html.Div([
                html.Label("Saved Project"),
                dcc.Dropdown(
                    id="saved-project-dropdown",
                    options=project_options,
                    value=project_options[0]["value"] if project_options else None,
                    placeholder="Load a saved setup",
                ),
            ], className="mb-3"),
            html.Div([
                html.Label("Project Name"),
                dcc.Input(
                    id="project-name-input",
                    type="text",
                    value="BTC Scalping Demo",
                    className="form-control",
                ),
            ], className="mb-3"),
            html.Div([
                html.Label("Strategy"),
                dcc.Dropdown(id="strategy-dropdown", options=STRATEGY_OPTIONS, value="market_order"),
            ], className="mb-3"),
            dbc.Button("Save Trading Project", id="save-project-button", color="secondary", className="w-100"),
            html.Small(id="project-status", className="text-muted d-block mt-2"),
        ]),
    ], className="h-100")


def _input_panel(exchange_options: list[dict[str, str]], default_symbol: str) -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader("Input Parameters"),
        dbc.CardBody([
            html.Div([
                html.Label("Exchange"),
                dcc.Dropdown(
                    id="exchange-dropdown",
                    options=exchange_options,
                    value=exchange_options[0]["value"],
                ),
            ], className="mb-3"),
            html.Div([
                html.Label("Market Type"),
                dcc.Dropdown(id="market-type-dropdown", options=MARKET_TYPE_OPTIONS, value="spot"),
            ], className="mb-3"),
            html.Div([
                html.Label("Symbol"),
                dcc.Input(id="symbol-input", type="text", value=default_symbol, className="form-control"),
            ], className="mb-3"),
            html.Div([
                html.Label("Order Side"),
                dcc.Dropdown(id="side-dropdown", options=SIDE_OPTIONS, value="buy"),
            ], className="mb-3"),
            html.Div([
                html.Label("Quantity (USD)"),
                dcc.Input(id="quantity-input", type="number", value=100, min=1, className="form-control"),
            ], className="mb-3"),
            html.Div([
                html.Label("Volatility"),
                dcc.Slider(
                    id="volatility-slider",
                    min=0.001,
                    max=0.05,
                    step=0.001,
                    value=0.01,
                    marks=VOLATILITY_MARKS,
                ),
            ], className="mb-3"),
            html.Div([
                html.Label("Fee Tier"),
                dcc.Dropdown(id="fee-tier-dropdown", options=FEE_TIER_OPTIONS, value="VIP0"),
            ], className="mb-3"),
            dbc.Button("Simulate", id="simulate-button", color="primary", className="w-100 mt-4"),
        ]),
    ], className="h-100")


def _results_panel() -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader("Simulation Results"),
        dbc.CardBody([
            html.Div([
                html.H5(label),
                html.P("--", id=field_id, className="metric-value"),
            ], className="mb-3")
            for field_id, label in METRIC_FIELDS
        ]),
    ], className="h-100")


def _chart_card(title: str, graph_id: str, figure) -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(dcc.Graph(id=graph_id, figure=figure, style={"height": "360px"})),
    ], className="mt-4")


def _history_panel() -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader("Simulation History"),
        dbc.CardBody(html.Div(id="history-table", children=html.P(
            "Run a simulation to start building history.", className="text-muted"
        ))),
    ], className="mt-4")


def _status_panel() -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader("Connection Status"),
        dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.Label("Feed"),
                html.P("--", id="feed-source-status"),
            ]), md=4),
            dbc.Col(html.Div([
                html.Label("Status"),
                html.P("Not connected", id="connection-status"),
            ]), md=4),
            dbc.Col(html.Div([
                html.Label("Last Update"),
                html.P("--", id="last-update-time"),
            ]), md=4),
        ])),
    ], className="mt-4")


def build_layout(
    project_options: list[dict[str, str]],
    exchange_options: list[dict[str, str]],
    default_symbol: str,
    refresh_interval_ms: int = 1000,
) -> dbc.Container:
    """Assemble the full dashboard layout."""
    return dbc.Container([
        _header(),
        _ticker_strip(),
        dbc.Row([
            dbc.Col(_project_panel(project_options), lg=4),
            dbc.Col(_input_panel(exchange_options, default_symbol), lg=4),
            dbc.Col(_results_panel(), lg=4),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(_chart_card("Order Book Depth", "orderbook-graph",
                                figures.placeholder("Waiting for order book data")), lg=6),
            dbc.Col(_chart_card("Mid Price", "price-history-graph",
                                figures.placeholder("Collecting price history")), lg=6),
        ]),
        dbc.Row([
            dbc.Col(_chart_card("Cost Breakdown", "cost-breakdown-graph",
                                figures.placeholder("Run a simulation to view cost breakdown")), lg=6),
            dbc.Col(_history_panel(), lg=6),
        ]),
        dbc.Row([dbc.Col(_status_panel(), width=12)]),
        dcc.Store(id="simulation-history", data=[]),
        dcc.Interval(id="interval-component", interval=refresh_interval_ms, n_intervals=0),
    ], fluid=True)
