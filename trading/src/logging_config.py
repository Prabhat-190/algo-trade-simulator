"""Logging setup. Call once from the app entrypoint."""
import logging
import os

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_configured = False


def configure_logging(level: str | None = None) -> None:
    global _configured
    if _configured:
        return

    resolved = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(level=getattr(logging, resolved, logging.INFO), format=LOG_FORMAT)

    # dash/werkzeug is noisy at INFO
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    _configured = True
