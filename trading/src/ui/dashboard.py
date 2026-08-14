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
    def __init__(self, simulator, project_store=None):
        """
        Initialize the dashboard.

        Args:
            simulator: Trade simulator instance
            project_store: Optional Redis-backed project store
        """
        self.simulator = simulator
        self.project_store = project_store
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # Initialize app layout
        self.init_layout()

        # Set up callbacks
        self.init_callbacks()

    def init_layout(self):
        """
        Initialize the dashboard layout.
        """
        project_options = self.project_store.list_projects() if self.project_store else []

        project_panel = dbc.Card([
            dbc.CardHeader("Trading Project"),
            dbc.CardBody([
                html.Div([
                    html.Label("Saved Project"),
                    dcc.Dropdown(
                        id='saved-project-dropdown',
                        options=project_options,
                        value=project_options[0]['value'] if project_options else None,
                        placeholder='Load a saved setup'
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Project Name"),
                    dcc.Input(
                        id='project-name-input',
                        type='text',
                        value='BTC Scalping Demo',
                        className="form-control"
                    )
                ], className="mb-3"),

                html.Div([
                    html.Label("Strategy"),
                    dcc.Dropdown(
                        id='strategy-dropdown',
                        options=[
                            {'label': 'Market Order Simulation', 'value': 'market_order'},
                            {'label': 'Scalping Cost Check', 'value': 'scalping'},
                            {'label': 'Swing Trade Cost Check', 'value': 'swing'},
                            {'label': 'Large Order Impact Check', 'value': 'large_order'}
                        ],
                        value='market_order'
                    )
                ], className="mb-3"),

                dbc.Button("Save Trading Project", id="save-project-button", color="secondary", className="w-100"),
                html.Small(id="project-status", className="text-muted d-block mt-2")
            ])
        ], className="h-100")

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

        output_panel = dbc.Card([
            dbc.CardHeader("Simulation Results"),
            dbc.CardBody([
                html.Div(id="simulation-results", children=[
                    html.Div([
                        html.H5("Project Summary"),
                        html.P(id="project-summary-output", children="--")
                    ], className="mb-3"),
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

        orderbook_viz = dbc.Card([
            dbc.CardHeader("Orderbook Visualization"),
            dbc.CardBody([
                dcc.Graph(
                    id="orderbook-graph",
                    figure=self.create_orderbook_visualization(),
                    style={"height": "400px"}
                )
            ])
        ], className="mt-4")

        cost_viz = dbc.Card([
            dbc.CardHeader("Cost Breakdown"),
            dbc.CardBody([
                dcc.Graph(
                    id="cost-breakdown-graph",
                    figure=self.create_empty_visualization("Run simulation to view cost breakdown"),
                    style={"height": "400px"}
                )
            ])
        ], className="mt-4")

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

        self.app.layout = dbc.Container([
            html.H1("Trade Simulator", className="my-4"),

            dbc.Row([
                dbc.Col(project_panel, width=4),
                dbc.Col(input_panel, width=4),
                dbc.Col(output_panel, width=4)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(orderbook_viz, width=6),
                dbc.Col(cost_viz, width=6)
            ], className="mb-4"),

            dbc.Row([
                dbc.Col(connection_status, width=12)
            ]),

            dcc.Interval(
                id='interval-component',
                interval=1000,
                n_intervals=0
            )
        ], fluid=True)

    def init_callbacks(self):
        """
        Initialize the dashboard callbacks.
        """
        @self.app.callback(
            [
                Output('saved-project-dropdown', 'options'),
                Output('saved-project-dropdown', 'value'),
                Output('project-status', 'children')
            ],
            [Input('save-project-button', 'n_clicks')],
            [
                State('project-name-input', 'value'),
                State('strategy-dropdown', 'value'),
                State('exchange-dropdown', 'value'),
                State('market-type-dropdown', 'value'),
                State('symbol-input', 'value'),
                State('side-dropdown', 'value'),
                State('quantity-input', 'value'),
                State('volatility-slider', 'value'),
                State('fee-tier-dropdown', 'value')
            ],
            prevent_initial_call=True
        )
        def save_project(n_clicks, name, strategy, exchange, market_type, symbol, side, quantity, volatility, fee_tier):
            if not self.project_store:
                return [], None, "Project store is not configured."
            from src.models.trading_project import TradingProject
            project = TradingProject.from_dict({
                'name': name,
                'strategy': strategy,
                'exchange': exchange,
                'market_type': market_type,
                'symbol': symbol,
                'side': side,
                'quantity_usd': quantity,
                'volatility': volatility,
                'fee_tier': fee_tier,
            })
            self.project_store.save(project)
            return self.project_store.list_projects(), project.name, f"Saved project: {project.name}"

        @self.app.callback(
            [
                Output('project-name-input', 'value'),
                Output('strategy-dropdown', 'value'),
                Output('exchange-dropdown', 'value'),
                Output('market-type-dropdown', 'value'),
                Output('symbol-input', 'value'),
                Output('side-dropdown', 'value'),
                Output('quantity-input', 'value'),
                Output('volatility-slider', 'value'),
                Output('fee-tier-dropdown', 'value')
            ],
            [Input('saved-project-dropdown', 'value')]
        )
        def load_project(project_name):
            if not self.project_store or not project_name:
                raise dash.exceptions.PreventUpdate
            project = self.project_store.get(project_name)
            if not project:
                raise dash.exceptions.PreventUpdate
            return (
                project.name,
                project.strategy,
                project.exchange,
                project.market_type,
                project.symbol,
                project.side,
                project.quantity_usd,
                project.volatility,
                project.fee_tier,
            )

        @self.app.callback(
            [
                Output("project-summary-output", "children"),
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
                State("project-name-input", "value"),
                State("strategy-dropdown", "value"),
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
        def simulate_order(n_clicks, project_name, strategy, exchange, market_type, symbol, side, quantity, volatility, fee_tier):
            """
            Simulate an order and update the UI.
            """
            if n_clicks is None:
                return ["--"] * 7 + [
                    self.create_orderbook_visualization(),
                    self.create_empty_visualization("Run simulation to view cost breakdown")
                ]

            mid_price = self.simulator.orderbook.get_mid_price()
            if mid_price is None or mid_price == 0:
                return ["Orderbook not available"] * 7 + [
                    self.create_orderbook_visualization(),
                    self.create_empty_visualization("Orderbook data is required for cost breakdown")
                ]

            base_quantity = quantity / mid_price

            result = self.simulator.simulate_market_order(
                side=side,
                quantity=base_quantity,
                exchange=exchange,
                market_type=market_type,
                fee_tier=fee_tier,
                volatility=volatility
            )

            if 'error' in result:
                return [result['error']] * 7 + [
                    self.create_orderbook_visualization(),
                    self.create_empty_visualization(result['error'])
                ]

            strategy_label = (strategy or 'market_order').replace('_', ' ').title()
            project_summary_output = f"{project_name or 'Untitled Project'} | {strategy_label} | {symbol} | {side.upper()} ${quantity:,.2f}"
            slippage_output = f"${result['slippage']:.4f} ({result['slippage_percentage']:.4f}%)"
            fees_output = f"${result['fees']['total_fee']:.4f} ({result['fees']['effective_rate'] * 100:.4f}%)"
            market_impact_output = f"${result['market_impact']['total_impact']:.4f} ({result['market_impact_percentage']:.4f}%)"
            net_cost_output = f"${result['net_cost']:.4f} ({result['net_cost_percentage']:.4f}%)"
            maker_taker_output = f"Maker: {result['maker_proportion'] * 100:.2f}% / Taker: {(1 - result['maker_proportion']) * 100:.2f}%"
            latency_output = f"{result['processing_time']:.2f} ms"

            orderbook_fig = self.create_orderbook_visualization()
            cost_breakdown_fig = self.create_cost_breakdown_visualization(result)

            return [
                project_summary_output,
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

    def apply_chart_theme(self, fig: go.Figure) -> go.Figure:
        """
        Apply the dashboard dark theme to Plotly figures.
        """
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(4,6,10,0.72)',
            font={'color': '#ffffff'},
            title_font={'color': '#ffffff'},
            legend={
                'font': {'color': '#ffffff'},
                'bgcolor': 'rgba(4,6,10,0.45)',
                'bordercolor': 'rgba(255,255,255,0.15)',
                'borderwidth': 1
            },
            margin={'l': 48, 'r': 24, 't': 56, 'b': 48}
        )
        fig.update_xaxes(
            color='#ffffff',
            gridcolor='rgba(176,196,222,0.18)',
            zerolinecolor='rgba(176,196,222,0.35)',
            linecolor='rgba(176,196,222,0.35)'
        )
        fig.update_yaxes(
            color='#ffffff',
            gridcolor='rgba(176,196,222,0.18)',
            zerolinecolor='rgba(176,196,222,0.35)',
            linecolor='rgba(176,196,222,0.35)'
        )
        return fig

    def create_empty_visualization(self, message: str) -> go.Figure:
        """
        Create a themed placeholder figure so charts are visible before data arrives.
        """
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            x=0.5,
            y=0.5,
            xref='paper',
            yref='paper',
            showarrow=False,
            font={'size': 16, 'color': '#b0c4de'}
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return self.apply_chart_theme(fig)

    def create_orderbook_visualization(self) -> go.Figure:
        """
        Create a visualization of the orderbook.

        Returns:
            go.Figure: Plotly figure
        """
        asks_df, bids_df = self.simulator.orderbook.to_dataframe()

        fig = go.Figure()

        if asks_df.empty and bids_df.empty:
            return self.create_empty_visualization("Waiting for orderbook data")

        if not asks_df.empty:
            fig.add_trace(go.Bar(
                x=asks_df['price'],
                y=asks_df['quantity'],
                name='Asks',
                marker_color='#ff1744'
            ))

        if not bids_df.empty:
            fig.add_trace(go.Bar(
                x=bids_df['price'],
                y=bids_df['quantity'],
                name='Bids',
                marker_color='#00e676'
            ))

        fig.update_layout(
            title='Orderbook',
            xaxis_title='Price',
            yaxis_title='Quantity',
            barmode='overlay',
            bargap=0
        )

        return self.apply_chart_theme(fig)

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

        if not any(values):
            return self.create_empty_visualization("No cost values to display")

        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=values,
            hole=.3,
            marker={'colors': ['#ffd600', '#00e5ff', '#ff1744']},
            textfont={'color': '#ffffff'}
        )])

        fig.update_layout(
            title='Cost Breakdown'
        )

        return self.apply_chart_theme(fig)

    def run_server(self, debug=True, port=8050):
        """
        Run the dashboard server.

        Args:
            debug: Whether to run in debug mode
            port: Port to run on
        """
        try:
            self.app.run(debug=debug, port=port, host="0.0.0.0")
        except Exception:
            try:
                self.app.run_server(debug=debug, port=port, host="0.0.0.0")
            except Exception as e:
                logging.error(f"Failed to start dashboard: {e}")
