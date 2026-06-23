"""
Slippage estimation model using linear or quantile regression.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, QuantileRegressor
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            y: Target (observed slippage)
        """
        if X.shape[0] < 10:
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
            float: Estimated slippage in quote currency
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
            float: Estimated slippage in quote currency
        """
        # Simple heuristic: slippage increases with order size, spread, and volatility
        # and decreases with favorable orderbook imbalance
        base_slippage = spread * 0.5  # Half the spread as base slippage
        size_factor = np.log1p(order_size) * 0.1  # Logarithmic scaling for order size
        vol_factor = volatility * 2.0  # Volatility directly impacts slippage
        
        # Imbalance adjustment: negative for buys when bids > asks, positive for sells when asks > bids
        imbalance_factor = -orderbook_imbalance * spread * 0.3
        
        return base_slippage + size_factor + vol_factor + imbalance_factor
