"""Synthetic Level-2 order book generator used for demos and offline development.

Produces frames in the same shape as the live exchange feed so the simulator,
dashboard and tests can run without Redis, API keys or network access. The mid
price follows a geometric Brownian motion and depth decays exponentially away
from the touch, which keeps slippage and market-impact numbers in a believable
range instead of the flat book a naive generator would produce.
"""
from __future__ import annotations

import math
import random
import time

from ..config import FeedSettings


class SyntheticOrderbookFeed:
    """Generates a continuously evolving order book for a single symbol."""

    def __init__(self, settings: FeedSettings, seed: int | None = None):
        self.settings = settings
        self.symbol = settings.symbol
        self.exchange = settings.exchange
        self.depth = max(1, settings.synthetic_depth)
        self.volatility = max(1e-6, settings.synthetic_volatility)
        self.spread_fraction = max(1e-6, settings.synthetic_spread_bps / 10_000)
        self.mid_price = max(0.01, settings.synthetic_start_price)
        self._random = random.Random(seed)
        # Mean-reverts the book toward its starting price so long demo sessions
        # do not drift into absurd values.
        self._anchor_price = self.mid_price

    def step(self) -> dict:
        """Advance the price one tick and return the resulting order book frame."""
        self._advance_price()
        spread = self._current_spread()
        half_spread = spread / 2

        asks = self._build_side(self.mid_price + half_spread, direction=1)
        bids = self._build_side(self.mid_price - half_spread, direction=-1)

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "asset_class": "synthetic",
            "source": "synthetic generator",
            "asks": asks,
            "bids": bids,
        }

    def _advance_price(self) -> None:
        shock = self._random.gauss(0, self.volatility)
        reversion = 0.02 * math.log(self._anchor_price / self.mid_price)
        self.mid_price = max(0.01, self.mid_price * math.exp(shock + reversion))

    def _current_spread(self) -> float:
        # Jitter the spread so it breathes, floored so the book never crosses.
        jitter = 1 + self._random.uniform(-0.3, 0.8)
        return max(self.mid_price * 1e-7, self.mid_price * self.spread_fraction * jitter)

    def _build_side(self, touch_price: float, direction: int) -> list[list[float]]:
        """Build one side of the book, walking away from the touch price."""
        tick = max(self.mid_price * self.spread_fraction, self.mid_price * 1e-7)
        levels: list[list[float]] = []

        for index in range(self.depth):
            price = touch_price + direction * tick * index
            # Depth grows with distance from the touch, as on a real venue.
            base_size = 0.35 * math.exp(index * 0.18)
            size = base_size * self._random.uniform(0.6, 1.7)
            levels.append([round(price, 2), round(size, 6)])

        return levels
