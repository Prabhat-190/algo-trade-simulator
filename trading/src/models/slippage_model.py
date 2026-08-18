"""
Slippage estimation model using linear or quantile regression.
"""
import logging

import numpy as np
from sklearn.linear_model import LinearRegression, QuantileRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Heuristic weights for the unfitted fallback estimator. Tuned so a small order
# costs roughly half the spread per unit and a book-sized order costs a few
# multiples of it.
SIZE_SENSITIVITY = 0.5
VOLATILITY_SENSITIVITY = 20.0
IMBALANCE_SENSITIVITY = 0.3
MIN_IMBALANCE_MULTIPLIER = 0.1

# Minimum training rows before a regression is worth fitting.
MIN_TRAINING_SAMPLES = 10


class SlippageModel:
    """
    Model for estimating slippage based on orderbook data.
    """
    def __init__(self, regression_type: str = 'linear', quantile: float = 0.5):
        """
        Initialize the slippage model.

        Args:
            regression_type: Type of regression ('linear' or 'quantile')
            quantile: Quantile for quantile regression (default: 0.5)
        """
        self.regression_type = regression_type
        self.quantile = quantile
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray):
        """
        Fit the slippage model.

        Args:
            X: Features (e.g., order size, spread, volatility)
            y: Target — observed *total* slippage cost in quote currency, matching
                what ``estimate_slippage`` is expected to return
        """
        if X.shape[0] < MIN_TRAINING_SAMPLES:
            logger.warning("Not enough data to fit slippage model")
            return

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Create and fit the model
        if self.regression_type == 'linear':
            self.model = LinearRegression()
        elif self.regression_type == 'quantile':
            self.model = QuantileRegressor(quantile=self.quantile, alpha=0.5)
        else:
            raise ValueError(f"Unknown regression type: {self.regression_type}")

        self.model.fit(X_scaled, y)
        self.is_fitted = True
        logger.info(f"Fitted {self.regression_type} slippage model")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict slippage for given features.

        Args:
            X: Features (e.g., order size, spread, volatility)

        Returns:
            np.ndarray: Predicted slippage
        """
        if not self.is_fitted:
            logger.warning("Slippage model not fitted yet")
            return np.zeros(X.shape[0])

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict
        return self.model.predict(X_scaled)

    def estimate_slippage(self,
                         order_size: float,
                         spread: float,
                         volatility: float,
                         orderbook_imbalance: float) -> float:
        """
        Estimate slippage for a market order.

        Args:
            order_size: Size of the order in base currency
            spread: Current spread in quote currency
            volatility: Current volatility
            orderbook_imbalance: Current orderbook imbalance

        Returns:
            float: Estimated *total* slippage cost in quote currency for the whole
                order, not a per-unit price concession
        """
        if not self.is_fitted:
            # Fallback estimation if model not fitted
            return self._estimate_slippage_fallback(order_size, spread, volatility, orderbook_imbalance)

        # Create feature vector
        X = np.array([[order_size, spread, volatility, orderbook_imbalance]])

        # Predict slippage
        return float(self.predict(X)[0])

    def _estimate_slippage_fallback(self,
                                  order_size: float,
                                  spread: float,
                                  volatility: float,
                                  orderbook_imbalance: float) -> float:
        """
        Fallback method to estimate slippage when model is not fitted.

        Args:
            order_size: Size of the order in base currency
            spread: Current spread in quote currency
            volatility: Current volatility
            orderbook_imbalance: Current orderbook imbalance

        Returns:
            float: Estimated total slippage cost in quote currency
        """
        # Crossing the spread costs at least half of it per unit traded.
        half_spread = spread * 0.5

        # Larger orders walk further into the book, so the concession per unit
        # grows with size. Logarithmic to avoid exploding on very large orders.
        size_multiplier = 1.0 + SIZE_SENSITIVITY * np.log1p(max(order_size, 0.0))

        # More volatile markets quote defensively, widening realised slippage.
        vol_multiplier = 1.0 + VOLATILITY_SENSITIVITY * volatility

        # A book leaning in the trade's favour reduces the concession; floored so
        # an extreme imbalance can never produce negative slippage.
        imbalance_multiplier = max(
            MIN_IMBALANCE_MULTIPLIER,
            1.0 - IMBALANCE_SENSITIVITY * orderbook_imbalance,
        )

        per_unit_slippage = half_spread * size_multiplier * vol_multiplier * imbalance_multiplier
        return max(0.0, per_unit_slippage * order_size)
