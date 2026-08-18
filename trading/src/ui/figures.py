"""Plotly figure builders for the dashboard.

Kept separate from layout and callbacks so charts can be unit tested without
constructing a Dash app.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

COLOR_BID = "#00e676"
COLOR_ASK = "#ff1744"
COLOR_FEES = "#ffd600"
COLOR_SLIPPAGE = "#00e5ff"
COLOR_IMPACT = "#ff1744"
COLOR_TEXT = "#ffffff"
COLOR_MUTED = "#b0c4de"


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the dark dashboard theme so charts stay readable on the dark page."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(4,6,10,0.72)",
        font={"color": COLOR_TEXT},
        title_font={"color": COLOR_TEXT},
        legend={
            "font": {"color": COLOR_TEXT},
            "bgcolor": "rgba(4,6,10,0.45)",
            "bordercolor": "rgba(255,255,255,0.15)",
            "borderwidth": 1,
        },
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
    )
    axis_style = {
        "color": COLOR_TEXT,
        "gridcolor": "rgba(176,196,222,0.18)",
        "zerolinecolor": "rgba(176,196,222,0.35)",
        "linecolor": "rgba(176,196,222,0.35)",
    }
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    return fig


def placeholder(message: str) -> go.Figure:
    """A themed empty chart, so the card is never a blank white box."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": COLOR_MUTED},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_theme(fig)


def depth_chart(asks_df: pd.DataFrame, bids_df: pd.DataFrame) -> go.Figure:
    """Cumulative depth ("staircase") view of the book.

    Cumulative depth shows how far a given order size would walk the book,
    which is what the cost model is actually estimating.
    """
    if asks_df.empty and bids_df.empty:
        return placeholder("Waiting for order book data")

    fig = go.Figure()

    if not bids_df.empty:
        fig.add_trace(go.Scatter(
            x=bids_df["price"],
            y=bids_df["cumulative_quantity"],
            name="Bids",
            mode="lines",
            line={"color": COLOR_BID, "width": 2, "shape": "hv"},
            fill="tozeroy",
            fillcolor="rgba(0,230,118,0.18)",
        ))

    if not asks_df.empty:
        fig.add_trace(go.Scatter(
            x=asks_df["price"],
            y=asks_df["cumulative_quantity"],
            name="Asks",
            mode="lines",
            line={"color": COLOR_ASK, "width": 2, "shape": "hv"},
            fill="tozeroy",
            fillcolor="rgba(255,23,68,0.18)",
        ))

    fig.update_layout(
        title="Order Book Depth",
        xaxis_title="Price",
        yaxis_title="Cumulative Quantity",
        hovermode="x unified",
    )
    return apply_theme(fig)


def cost_breakdown_chart(result: dict) -> go.Figure:
    """Donut chart splitting net cost into fees, slippage and market impact."""
    values = [
        result["fees"]["total_fee"],
        result["slippage"],
        result["market_impact"]["total_impact"],
    ]

    if not any(values):
        return placeholder("No cost values to display")

    fig = go.Figure(data=[go.Pie(
        labels=["Fees", "Slippage", "Market Impact"],
        values=values,
        hole=0.45,
        marker={"colors": [COLOR_FEES, COLOR_SLIPPAGE, COLOR_IMPACT]},
        textfont={"color": COLOR_TEXT},
        hovertemplate="%{label}: $%{value:.4f} (%{percent})<extra></extra>",
    )])
    fig.update_layout(title="Cost Breakdown")
    return apply_theme(fig)


def price_history_chart(history: list[tuple[float, float]]) -> go.Figure:
    """Mid price over the session, so a live feed is visibly live."""
    if len(history) < 2:
        return placeholder("Collecting price history")

    timestamps = [pd.to_datetime(ts, unit="s") for ts, _ in history]
    prices = [price for _, price in history]
    rising = prices[-1] >= prices[0]
    color = COLOR_BID if rising else COLOR_ASK

    fig = go.Figure(go.Scatter(
        x=timestamps,
        y=prices,
        mode="lines",
        name="Mid Price",
        line={"color": color, "width": 2},
        fill="tozeroy",
        fillcolor="rgba(0,230,118,0.12)" if rising else "rgba(255,23,68,0.12)",
    ))
    fig.update_layout(
        title="Mid Price",
        xaxis_title="Time",
        yaxis_title="Price",
        hovermode="x unified",
    )
    fig.update_yaxes(autorange=True)
    return apply_theme(fig)
