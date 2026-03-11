"""
Dashboard UI for the trade simulator using Dash.
"""
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Dashboard:
    """
    Dashboard UI for the trade simulator.
    """
    def __init__(self, simulator):
        """
        Initialize the dashboard.

        Args:
            simulator: Trade simulator instance
        """
        self.simulator = simulator
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # Initialize app layout
        self.init_layout()

        # Set up callbacks
        self.init_callbacks()

    def init_layout(self):
        """
        Initialize the dashboard layout.
        """
        # Input parameters panel
        input_panel = dbc.Card([
            dbc.CardHeader("Input Parameters"),
            dbc.CardBody([
                html.Div([
                    html.Label("Exchange"),
                    dcc.Dropdown(
                        id='exchange-dropdown',
                        options=[{'label': 'OKX', 'value': 'OKX'}],
                        value='OKX'
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Market Type"),
                    dcc.Dropdown(
                        id='market-type-dropdown',
                        options=[
                            {'label': 'Spot', 'value': 'spot'},
                            {'label': 'Futures', 'value': 'futures'}
                        ],
                        value='spot'
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Symbol"),
                    dcc.Input(
                        id='symbol-input',
                        type='text',
                        value='BTC-USDT',
                        className="form-control"
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Order Side"),
                    dcc.Dropdown(
                        id='side-dropdown',
                        options=[
                            {'label': 'Buy', 'value': 'buy'},
                            {'label': 'Sell', 'value': 'sell'}
                        ],
                        value='buy'
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Quantity (USD)"),
                    dcc.Input(
                        id='quantity-input',
                        type='number',
                        value=100,
                        min=1,
                        className="form-control"
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Volatility"),
                    dcc.Slider(
                        id='volatility-slider',
                        min=0.001,
                        max=0.05,
                        step=0.001,
                        value=0.01,
                        marks={
                            0.001: '0.1%',
                            0.01: '1%',
                            0.02: '2%',
                            0.03: '3%',
                            0.04: '4%',
                            0.05: '5%'
                        }
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Fee Tier"),
                    dcc.Dropdown(
                        id='fee-tier-dropdown',
                        options=[
                            {'label': 'VIP0', 'value': 'VIP0'},
                            {'label': 'VIP1', 'value': 'VIP1'},
                            {'label': 'VIP2', 'value': 'VIP2'},
                            {'label': 'VIP3', 'value': 'VIP3'},
                            {'label': 'VIP4', 'value': 'VIP4'},
                            {'label': 'VIP5', 'value': 'VIP5'}
                        ],
                        value='VIP0'
                    )
                ], className="mb-3"),

                html.Div([
                    dbc.Button("Simulate", id="simulate-button", color="primary", className="w-100")
                ], className="mt-4")
            ])
        ], className="h-100")

        # Output parameters panel
        output_panel = dbc.Card([
            dbc.CardHeader("Simulation Results"),
            dbc.CardBody([
                html.Div(id="simulation-results", children=[
                    html.Div([
                        html.H5("Expected Slippage"),
                        html.P(id="slippage-output", children="--")
                    ], className="mb-3"),

                    html.Div([
                        html.H5("Expected Fees"),
                        html.P(id="fees-output", children="--")
                    ], className="mb-3"),

                    html.Div([
                        html.H5("Expected Market Impact"),
                        html.P(id="market-impact-output", children="--")
                    ], className="mb-3"),

                    html.Div([
                        html.H5("Net Cost"),
                        html.P(id="net-cost-output", children="--")
                    ], className="mb-3"),

                    html.Div([
                        html.H5("Maker/Taker Proportion"),
                        html.P(id="maker-taker-output", children="--")
                    ], className="mb-3"),

                    html.Div([
                        html.H5("Internal Latency"),
                        html.P(id="latency-output", children="--")
                    ], className="mb-3")
                ])
            ])
        ], className="h-100")

        # Orderbook visualization
        orderbook_viz = dbc.Card([
            dbc.CardHeader("Orderbook Visualization"),
            dbc.CardBody([
                dcc.Graph(id="orderbook-graph", style={"height": "400px"})
            ])
        ], className="mt-4")

        # Cost breakdown visualization
        cost_viz = dbc.Card([
            dbc.CardHeader("Cost Breakdown"),
            dbc.CardBody([
                dcc.Graph(id="cost-breakdown-graph", style={"height": "400px"})
            ])
        ], className="mt-4")

        # Connection status
        connection_status = dbc.Card([
            dbc.CardHeader("Connection Status"),
            dbc.CardBody([
                html.Div([
                    html.P(id="connection-status", children="Not connected")
                ]),
                html.Div([
                    html.P(id="last-update-time", children="--")
                ])
            ])
        ], className="mt-4")

        # Main layout
        self.app.layout = dbc.Container([
            html.H1("Trade Simulator", className="my-4"),

            dbc.Row([
                dbc.Col(input_panel, width=4),
                dbc.Col(output_panel, width=8)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(orderbook_viz, width=6),
                dbc.Col(cost_viz, width=6)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(connection_status, width=12)
            ]),

            # Add interval component for periodic updates
            dcc.Interval(
                id='interval-component',
                interval=1000,  # in milliseconds
                n_intervals=0
            )
        ], fluid=True)

    def init_callbacks(self):
        """
        Initialize the dashboard callbacks.
        """
        @self.app.callback(
            [
                Output("slippage-output", "children"),
                Output("fees-output", "children"),
                Output("market-impact-output", "children"),
                Output("net-cost-output", "children"),
                Output("maker-taker-output", "children"),
                Output("latency-output", "children"),
                Output("orderbook-graph", "figure"),
                Output("cost-breakdown-graph", "figure")
            ],
            [Input("simulate-button", "n_clicks")],
            [
                State("exchange-dropdown", "value"),
                State("market-type-dropdown", "value"),
                State("symbol-input", "value"),
                State("side-dropdown", "value"),
                State("quantity-input", "value"),
                State("volatility-slider", "value"),
                State("fee-tier-dropdown", "value")
            ],
            prevent_initial_call=True
        )
        def simulate_order(n_clicks, exchange, market_type, symbol, side, quantity, volatility, fee_tier):
            """
            Simulate an order and update the UI.
            """
            if n_clicks is None:
                return ["--"] * 6 + [go.Figure(), go.Figure()]

            # Convert quantity from USD to base currency
            mid_price = self.simulator.orderbook.get_mid_price()
            if mid_price is None or mid_price == 0:
                return ["Orderbook not available"] * 6 + [go.Figure(), go.Figure()]

            base_quantity = quantity / mid_price

            # Simulate the order
            result = self.simulator.simulate_market_order(
                side=side,
                quantity=base_quantity,
                exchange=exchange,
                market_type=market_type,
                fee_tier=fee_tier,
                volatility=volatility
            )

            if 'error' in result:
                return [result['error']] * 6 + [go.Figure(), go.Figure()]

            # Format outputs
            slippage_output = f"${result['slippage']:.4f} ({result['slippage_percentage']:.4f}%)"
            fees_output = f"${result['fees']['total_fee']:.4f} ({result['fees']['effective_rate'] * 100:.4f}%)"
            market_impact_output = f"${result['market_impact']['total_impact']:.4f} ({result['market_impact_percentage']:.4f}%)"
            net_cost_output = f"${result['net_cost']:.4f} ({result['net_cost_percentage']:.4f}%)"
            maker_taker_output = f"Maker: {result['maker_proportion'] * 100:.2f}% / Taker: {(1 - result['maker_proportion']) * 100:.2f}%"
            latency_output = f"{result['processing_time']:.2f} ms"

            # Create orderbook visualization
            orderbook_fig = self.create_orderbook_visualization()

            # Create cost breakdown visualization
            cost_breakdown_fig = self.create_cost_breakdown_visualization(result)

            return [
                slippage_output,
                fees_output,
                market_impact_output,
                net_cost_output,
                maker_taker_output,
                latency_output,
                orderbook_fig,
                cost_breakdown_fig
            ]

        @self.app.callback(
            [
                Output("connection-status", "children"),
                Output("last-update-time", "children")
            ],
            [Input("interval-component", "n_intervals")]
        )
        def update_connection_status(n_intervals):
            """
            Update the connection status.
            """
            if self.simulator.last_update_time == 0:
                status = "Not connected"
                last_update = "--"
            else:
                time_since_update = time.time() - self.simulator.last_update_time
                if time_since_update < 5:
                    status = "Connected"
                else:
                    status = f"Last update {time_since_update:.1f} seconds ago"

                last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.simulator.last_update_time))

            return status, f"Last update: {last_update}"

    def create_orderbook_visualization(self) -> go.Figure:
        """
        Create a visualization of the orderbook.

        Returns:
            go.Figure: Plotly figure
        """
        asks_df, bids_df = self.simulator.orderbook.to_dataframe()

        fig = go.Figure()

        if not asks_df.empty:
            fig.add_trace(go.Bar(
                x=asks_df['price'],
                y=asks_df['quantity'],
                name='Asks',
                marker_color='red'
            ))

        if not bids_df.empty:
            fig.add_trace(go.Bar(
                x=bids_df['price'],
                y=bids_df['quantity'],
                name='Bids',
                marker_color='green'
            ))

        fig.update_layout(
            title='Orderbook',
            xaxis_title='Price',
            yaxis_title='Quantity',
            barmode='overlay',
            bargap=0
        )

        return fig

    def create_cost_breakdown_visualization(self, result: Dict) -> go.Figure:
        """
        Create a visualization of the cost breakdown.

        Args:
            result: Simulation result

        Returns:
            go.Figure: Plotly figure
        """
        categories = ['Fees', 'Slippage', 'Market Impact']
        values = [
            result['fees']['total_fee'],
            result['slippage'],
            result['market_impact']['total_impact']
        ]

        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=values,
            hole=.3
        )])

        fig.update_layout(
            title='Cost Breakdown'
        )

        return fig

    def run_server(self, debug=True, port=8050):
        """
        Run the dashboard server.

        Args:
            debug: Whether to run in debug mode
            port: Port to run on
        """
        try:
            # Try the new method first
            self.app.run(debug=debug, port=port, host="0.0.0.0")
        except Exception as e:
            # Fall back to the old method
            try:
                self.app.run_server(debug=debug, port=port, host="0.0.0.0")
            except Exception as e:
                # If both fail, log the error
                logging.error(f"Failed to start dashboard: {e}")
