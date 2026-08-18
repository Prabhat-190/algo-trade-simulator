"""
Trade simulator optimized for reading cache layers and utilizing persisted ML models.
"""
import logging
import os
import time
from typing import Any

import joblib

from ..data.orderbook import Orderbook
from .fee_model import FeeModel
from .maker_taker import MakerTakerModel
from .market_impact import AlmgrenChrissModel
from .slippage_model import SlippageModel

logger = logging.getLogger(__name__)

# Order book depth is a snapshot, not a daily volume. Almgren-Chriss needs an
# average daily volume, so visible depth is scaled by this factor to approximate
# one. It is a rough proxy, exposed here rather than buried as a magic number.
DEPTH_TO_DAILY_VOLUME_FACTOR = 100

# An almost entirely one-sided book usually means bad data or spoofing.
MAX_PLAUSIBLE_IMBALANCE = 0.98

PROCESSING_TIME_SAMPLE_LIMIT = 1000

class TradeSimulator:
    """
    Simulator for estimating transaction costs and market impact of trades.
    """
    def __init__(self, models_dir: str | None = None):
        """
        Initialize the trade simulator.
        """
        self.orderbook = Orderbook()
        self.market_impact_model = AlmgrenChrissModel()
        self.fee_model = FeeModel()

        # Initialize ML Models
        self.maker_taker_model = MakerTakerModel()
        self.slippage_model = SlippageModel()

        # Load pre-trained weights if path is provided to prevent fallback resets
        if models_dir:
            self._load_persisted_models(models_dir)

        self.last_update_time = 0
        self.processing_times = []

    def _load_persisted_models(self, models_dir: str):
        """
        Loads pre-trained machine learning models from disk.
        """
        try:
            mt_path = os.path.join(models_dir, 'maker_taker_model.joblib')
            slip_path = os.path.join(models_dir, 'slippage_model.joblib')

            if os.path.exists(mt_path):
                self.maker_taker_model.model, self.maker_taker_model.scaler = joblib.load(mt_path)
                self.maker_taker_model.is_fitted = True
                logger.info("Successfully loaded persisted Maker/Taker model weights.")

            if os.path.exists(slip_path):
                self.slippage_model.model, self.slippage_model.scaler = joblib.load(slip_path)
                self.slippage_model.is_fitted = True
                logger.info("Successfully loaded persisted Slippage model weights.")
        except Exception as e:
            logger.error(f"Failed to load persisted ML models, reverting to heuristics: {e}")

    def detect_orderbook_anomalies(self, imbalance: float, spread: float) -> bool:
        """
        Anomaly detection layer to intercept manipulation before cost calculations.
        """
        if abs(imbalance) > MAX_PLAUSIBLE_IMBALANCE or spread <= 0:
            logger.warning(f"Anomalous market state detected! Imbalance: {imbalance}, Spread: {spread}")
            return True
        return False

    def update_orderbook(self, data: dict) -> float:
        """
        Update the orderbook with new data.
        """
        start_time = time.time()

        self.orderbook.update(data)

        self.last_update_time = time.time()
        # Floored so callers can always treat the value as a positive duration.
        total_processing_time = max((self.last_update_time - start_time) * 1000, 0.001)

        self.processing_times.append(total_processing_time)
        if len(self.processing_times) > PROCESSING_TIME_SAMPLE_LIMIT:
            self.processing_times = self.processing_times[-PROCESSING_TIME_SAMPLE_LIMIT:]

        return total_processing_time

    def simulate_market_order(self,
                             side: str,
                             quantity: float,
                             exchange: str = 'OKX',
                             market_type: str = 'spot',
                             fee_tier: str = 'VIP0',
                             volatility: float = 0.01) -> dict[str, Any]:
        """
        Simulate a market order and estimate transaction costs.
        """
        start_time = time.time()

        if quantity is None or quantity <= 0:
            return {'error': 'Quantity must be greater than zero'}

        if side.lower() not in ('buy', 'sell'):
            return {'error': f"Unknown order side: {side}"}

        # Check if orderbook is available
        if not self.orderbook.asks or not self.orderbook.bids:
            logger.warning("Orderbook is empty, cannot simulate order")
            return {
                'error': 'Orderbook is empty'
            }

        # Get orderbook metrics
        mid_price = self.orderbook.get_mid_price()
        spread = self.orderbook.get_spread()
        orderbook_imbalance = self.orderbook.get_orderbook_imbalance()

        if mid_price is None or spread is None or orderbook_imbalance is None:
            logger.warning("Invalid orderbook metrics")
            return {
                'error': 'Invalid orderbook metrics'
            }

        # Check for anomalies/manipulation signatures before processing order
        anomaly_detected = self.detect_orderbook_anomalies(orderbook_imbalance, spread)

        # Calculate order value
        order_value = quantity * mid_price

        # Estimate maker/taker proportion
        maker_proportion = self.maker_taker_model.estimate_maker_proportion(
            quantity, spread, volatility, orderbook_imbalance
        )

        # Calculate fees
        fees = self.fee_model.calculate_fee(
            order_value, exchange, market_type, fee_tier, maker_proportion
        )

        # Estimate slippage
        slippage = self.slippage_model.estimate_slippage(
            quantity, spread, volatility, orderbook_imbalance
        )

        # Calculate market impact
        orderbook_depth = sum(qty for _, qty in self.orderbook.bids) + sum(qty for _, qty in self.orderbook.asks)
        avg_daily_volume = orderbook_depth * DEPTH_TO_DAILY_VOLUME_FACTOR

        market_impact = self.market_impact_model.calculate_market_impact(
            quantity, avg_daily_volume, volatility, mid_price, orderbook_depth
        )

        # Calculate net cost
        net_cost = fees['total_fee'] + slippage + market_impact['total_impact']
        net_cost_percentage = (net_cost / order_value) * 100 if order_value > 0 else 0

        # Calculate execution price
        if side.lower() == 'buy':
            execution_price = mid_price + (slippage + market_impact['temporary_impact']) / quantity
        else:  # sell
            execution_price = mid_price - (slippage + market_impact['temporary_impact']) / quantity

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        # Return simulation results
        return {
            'timestamp': self.orderbook.timestamp,
            'exchange': exchange,
            'symbol': self.orderbook.symbol,
            'side': side,
            'quantity': quantity,
            'mid_price': mid_price,
            'execution_price': execution_price,
            'order_value': order_value,
            'maker_proportion': maker_proportion,
            'fees': fees,
            'slippage': slippage,
            'slippage_percentage': (slippage / order_value) * 100 if order_value > 0 else 0,
            'market_impact': market_impact,
            'market_impact_percentage': (market_impact['total_impact'] / order_value) * 100 if order_value > 0 else 0,
            'net_cost': net_cost,
            'net_cost_percentage': net_cost_percentage,
            'anomaly_flag': anomaly_detected,
            'processing_time': processing_time
        }

    def get_average_processing_time(self) -> float:
        """
        Get the average processing time for simulations.
        """
        if not self.processing_times:
            return 0

        return sum(self.processing_times) / len(self.processing_times)
