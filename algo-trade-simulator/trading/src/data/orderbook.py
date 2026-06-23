"""
Orderbook data structure for processing and analyzing L2 market data.
"""
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Orderbook:
    """
    Orderbook data structure for processing L2 market data.
    """
    def __init__(self, max_depth: int = 50):
        """
        Initialize the orderbook.

        Args:
            max_depth: Maximum number of price levels to maintain
        """
        self.max_depth = max_depth
        self.asks = []  # List of [price, quantity] pairs
        self.bids = []  # List of [price, quantity] pairs
        self.timestamp = None
        self.exchange = None
        self.symbol = None
        self.last_update_time = 0
        self.processing_times = []  # Track processing times for performance metrics

    def update(self, data: Dict) -> float:
        """
        Update the orderbook with new data.

        Args:
            data: Orderbook data with asks and bids

        Returns:
            float: Processing time in milliseconds
        """
        start_time = time.time()

        self.timestamp = data.get('timestamp')
        self.exchange = data.get('exchange')
        self.symbol = data.get('symbol')

        # Convert string prices and quantities to float
        asks = [[float(price), float(qty)] for price, qty in data.get('asks', [])]
        bids = [[float(price), float(qty)] for price, qty in data.get('bids', [])]

        # Update asks and bids
        self.asks = sorted(asks, key=lambda x: x[0])[:self.max_depth]
        self.bids = sorted(bids, key=lambda x: x[0], reverse=True)[:self.max_depth]

        self.last_update_time = time.time()
        processing_time = (self.last_update_time - start_time) * 1000  # Convert to ms
        self.processing_times.append(processing_time)

        # Keep only the last 1000 processing times
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]

        return processing_time

    def get_mid_price(self) -> Optional[float]:
        """
        Calculate the mid price (average of best bid and best ask).

        Returns:
            float: Mid price or None if orderbook is empty
        """
        if not self.asks or not self.bids:
            return None

        best_ask = self.asks[0][0]
        best_bid = self.bids[0][0]
        return (best_ask + best_bid) / 2

    def get_spread(self) -> Optional[float]:
        """
        Calculate the spread (difference between best ask and best bid).

        Returns:
            float: Spread or None if orderbook is empty
        """
        if not self.asks or not self.bids:
            return None

        best_ask = self.asks[0][0]
        best_bid = self.bids[0][0]
        return best_ask - best_bid

    def get_spread_percentage(self) -> Optional[float]:
        """
        Calculate the spread as a percentage of the mid price.

        Returns:
            float: Spread percentage or None if orderbook is empty
        """
        spread = self.get_spread()
        mid_price = self.get_mid_price()

        if spread is None or mid_price is None or mid_price == 0:
            return None

        return (spread / mid_price) * 100

    def get_volume_at_price(self, side: str, price: float) -> float:
        """
        Get the volume available at a specific price level.

        Args:
            side: 'ask' or 'bid'
            price: Price level

        Returns:
            float: Volume available at the price
        """
        if side.lower() == 'ask':
            for p, q in self.asks:
                if abs(p - price) < 1e-8:  # Compare with small epsilon for float comparison
                    return q
        elif side.lower() == 'bid':
            for p, q in self.bids:
                if abs(p - price) < 1e-8:
                    return q
        return 0.0

    def get_volume_up_to_price(self, side: str, price: float) -> float:
        """
        Get the cumulative volume up to a specific price level.

        Args:
            side: 'ask' or 'bid'
            price: Price level

        Returns:
            float: Cumulative volume
        """
        volume = 0.0

        if side.lower() == 'ask':
            for p, q in self.asks:
                if p <= price:
                    volume += q
                else:
                    break
        elif side.lower() == 'bid':
            for p, q in self.bids:
                if p >= price:
                    volume += q
                else:
                    break

        return volume

    def get_price_for_volume(self, side: str, volume: float) -> Optional[float]:
        """
        Get the price needed to fill a specific volume.

        Args:
            side: 'ask' or 'bid'
            volume: Volume to fill

        Returns:
            float: Price needed or None if not enough volume
        """
        remaining_volume = volume

        if side.lower() == 'ask':
            for p, q in self.asks:
                remaining_volume -= q
                if remaining_volume <= 0:
                    return p
        elif side.lower() == 'bid':
            for p, q in self.bids:
                remaining_volume -= q
                if remaining_volume <= 0:
                    return p

        return None  # Not enough volume in the orderbook

    def get_orderbook_imbalance(self) -> Optional[float]:
        """
        Calculate the orderbook imbalance (bid volume - ask volume) / (bid volume + ask volume).

        Returns:
            float: Imbalance between -1 and 1, or None if orderbook is empty
        """
        if not self.asks or not self.bids:
            return None

        bid_volume = sum(q for _, q in self.bids)
        ask_volume = sum(q for _, q in self.asks)

        if bid_volume + ask_volume == 0:
            return 0

        return (bid_volume - ask_volume) / (bid_volume + ask_volume)

    def get_average_processing_time(self) -> float:
        """
        Get the average processing time for orderbook updates.

        Returns:
            float: Average processing time in milliseconds
        """
        if not self.processing_times:
            return 0

        return sum(self.processing_times) / len(self.processing_times)

    def to_dataframe(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Convert the orderbook to pandas DataFrames.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (asks_df, bids_df)
        """
        asks_df = pd.DataFrame(self.asks, columns=['price', 'quantity'])
        bids_df = pd.DataFrame(self.bids, columns=['price', 'quantity'])

        # Add cumulative quantities
        if not asks_df.empty:
            asks_df['cumulative_quantity'] = asks_df['quantity'].cumsum()
        if not bids_df.empty:
            bids_df['cumulative_quantity'] = bids_df['quantity'].cumsum()

        return asks_df, bids_df
