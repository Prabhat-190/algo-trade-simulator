"""Single place where logging is configured.

Library modules only call ``logging.getLogger(__name__)``; entrypoints call
``configure_logging()`` once so that worker processes share one format.
"""
from __future__ import annotations

import logging
import os

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_configured = False


def configure_logging(level: str | None = None) -> None:
    """Configure root logging. Repeat calls are ignored."""
    global _configured
    if _configured:
        return

    resolved = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(level=getattr(logging, resolved, logging.INFO), format=LOG_FORMAT)

    # Dash logs every callback request at INFO, which drowns out everything else.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    _configured = True
