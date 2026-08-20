"""
Fake L2 book for local/demo runs (no redis / no exchange needed).
"""
import math
import random
import time

from ..config import FeedSettings


class SyntheticOrderbookFeed:
    def __init__(self, settings: FeedSettings, seed: int | None = None):
        self.settings = settings
        self.symbol = settings.symbol
        self.exchange = settings.exchange
        self.depth = max(1, settings.synthetic_depth)
        self.volatility = max(1e-6, settings.synthetic_volatility)
        self.spread_fraction = max(1e-6, settings.synthetic_spread_bps / 10_000)
        self.mid_price = max(0.01, settings.synthetic_start_price)
        self._random = random.Random(seed)
        self._anchor_price = self.mid_price  # pull price back if it drifts too far

    def step(self) -> dict:
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
        jitter = 1 + self._random.uniform(-0.3, 0.8)
        return max(self.mid_price * 1e-7, self.mid_price * self.spread_fraction * jitter)

    def _build_side(self, touch_price: float, direction: int) -> list[list[float]]:
        tick = max(self.mid_price * self.spread_fraction, self.mid_price * 1e-7)
        levels = []

        for i in range(self.depth):
            price = touch_price + direction * tick * i
            # a bit more size as we walk away from mid
            base_size = 0.35 * math.exp(i * 0.18)
            size = base_size * self._random.uniform(0.6, 1.7)
            levels.append([round(price, 2), round(size, 6)])

        return levels
