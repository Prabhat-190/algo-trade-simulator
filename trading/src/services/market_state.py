"""
Shared simulator state. Feed threads write, dash callbacks read.
"""
import logging
import threading
import time
from collections import deque
from typing import Any

import pandas as pd

from ..models.simulator import TradeSimulator

logger = logging.getLogger(__name__)


class MarketState:
    def __init__(self, simulator: TradeSimulator, history_size: int = 300):
        self._simulator = simulator
        self._lock = threading.RLock()
        self._price_history: deque[tuple[float, float]] = deque(maxlen=history_size)

    def apply_frame(self, frame: dict) -> None:
        with self._lock:
            try:
                self._simulator.update_orderbook(frame)
            except (KeyError, TypeError, ValueError) as exc:
                logger.error("Rejected malformed order book frame: %s", exc)
                return
            mid_price = self._simulator.orderbook.get_mid_price()

        if mid_price:
            self._price_history.append((time.time(), mid_price))

    def simulate_market_order(self, **kwargs: Any) -> dict[str, Any]:
        with self._lock:
            return self._simulator.simulate_market_order(**kwargs)

    def orderbook_frames(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        with self._lock:
            return self._simulator.orderbook.to_dataframe()

    def price_history(self) -> list[tuple[float, float]]:
        return list(self._price_history)

    @property
    def last_update_time(self) -> float:
        with self._lock:
            return self._simulator.last_update_time

    def snapshot(self) -> dict[str, float | None]:
        with self._lock:
            book = self._simulator.orderbook
            mid_price = book.get_mid_price()
            spread = book.get_spread()
            imbalance = book.get_orderbook_imbalance()
            depth = sum(qty for _, qty in book.bids) + sum(qty for _, qty in book.asks)
            symbol = book.symbol
            last_update = self._simulator.last_update_time

        return {
            "symbol": symbol,
            "mid_price": mid_price,
            "spread": spread,
            "spread_pct": (spread / mid_price * 100) if spread is not None and mid_price else None,
            "imbalance": imbalance,
            "depth": depth if (mid_price is not None) else None,
            "last_update": last_update,
        }
