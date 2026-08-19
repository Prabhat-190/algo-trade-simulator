"""Dash application assembly.

Wires the layout and callbacks onto a Dash instance. Layout construction lives
in ``layout.py``, chart building in ``figures.py`` and callback bodies in
``callbacks.py``.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dash
from werkzeug.middleware.proxy_fix import ProxyFix

from ..models.trading_project import TradingProjectStore
from ..services.market_state import MarketState
from . import callbacks as callback_module
from . import layout as layout_module

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"
PAGE_TITLE = "Algo Trade Simulator"

EXCHANGE_OPTIONS = [
    {"label": "OKX", "value": "OKX"},
    {"label": "Simulated", "value": "SIMULATED"},
]


class Dashboard:
    """Builds and owns the Dash app."""

    def __init__(
        self,
        market: MarketState,
        project_store: TradingProjectStore | None = None,
        feed_status: Callable[[], dict[str, Any]] | None = None,
        default_symbol: str = "BTC-USDT",
    ):
        self.market = market
        self.project_store = project_store

        # Stylesheets live in assets/ (including a vendored Bootstrap) so the
        # dashboard does not depend on a CDN. serve_locally keeps Plotly/Dash JS
        # on this origin, which avoids mixed-content failures behind Railway's
        # HTTPS proxy.
        self.app = dash.Dash(
            __name__,
            assets_folder=str(ASSETS_DIR),
            title=PAGE_TITLE,
            update_title=None,
            serve_locally=True,
            meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        )
        self.app.server.wsgi_app = ProxyFix(
            self.app.server.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1,
        )

        self.app.layout = layout_module.build_layout(
            project_options=project_store.list_projects() if project_store else [],
            exchange_options=EXCHANGE_OPTIONS,
            default_symbol=default_symbol,
        )
        callback_module.register_callbacks(
            self.app,
            market=market,
            project_store=project_store,
            feed_status=feed_status,
        )

    @property
    def server(self):
        """The underlying Flask app, for WSGI servers such as Gunicorn."""
        return self.app.server

    def run(self, host: str = "0.0.0.0", port: int = 8050, debug: bool = False) -> None:
        """Run Dash's development server. Production uses Gunicorn instead."""
        self.app.run(host=host, port=port, debug=debug)
