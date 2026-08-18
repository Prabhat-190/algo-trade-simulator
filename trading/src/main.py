"""Entrypoint for the dashboard.

Gunicorn imports ``server`` from this module:

    gunicorn trading.src.main:server

Running it directly starts the Dash development server instead.
"""
from __future__ import annotations

import argparse

from .app import create_app

# Gunicorn needs a module-level WSGI callable, so the app is built on import.
# Each worker therefore gets its own instance with its own feed threads, which is
# why the synthetic fallback feeds in-process instead of publishing to Redis.
_app = create_app()
server = _app.server


def main() -> None:
    settings = _app.settings
    parser = argparse.ArgumentParser(description="Run the Algo Trade Simulator dashboard.")
    parser.add_argument("--host", default=settings.host, help="Host interface to bind")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to bind")
    parser.add_argument("--debug", action="store_true", default=settings.debug,
                        help="Enable Dash debug mode")
    args = parser.parse_args()

    _app.dashboard.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
