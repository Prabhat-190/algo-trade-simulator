"""
Dashboard entrypoint.

gunicorn trading.src.main:server
"""
import argparse

from .app import create_app

# gunicorn imports this module, so the app has to exist at import time
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
