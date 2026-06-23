"""
Model for predicting maker/taker proportion using logistic regression.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MakerTakerModel:
    """
    Model for predicting the proportion of an order that will be executed as maker vs taker.
    """
    def __init__(self):
        """
        Initialize the maker/taker proportion model.
        """
        self.model = LogisticRegression(max_iter=1000)
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, X: np.ndarray, y: np.ndarray):
        """
        Fit the maker/taker model.
        
        Args:
            X: Features (e.g., order size, spread, volatility, orderbook imbalance)
            y: Target (1 for maker, 0 for taker)
        """
        if X.shape[0] < 10:
            logger.warning("Not enough data to fit maker/taker model")
            return
            
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        logger.info("Fitted maker/taker model")
        
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict maker probability for given features.
        
        Args:
            X: Features (e.g., order size, spread, volatility, orderbook imbalance)
            
        Returns:
            np.ndarray: Predicted maker probabilities
        """
        if not self.is_fitted:
            logger.warning("Maker/taker model not fitted yet")
            return np.ones(X.shape[0]) * 0.5  # Default to 50% maker
            
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict probabilities
        return self.model.predict_proba(X_scaled)[:, 1]  # Probability of class 1 (maker)
        
    def estimate_maker_proportion(self, 
                                order_size: float, 
                                spread: float, 
                                volatility: float, 
                                orderbook_imbalance: float) -> float:
        """
        Estimate the proportion of an order that will be executed as maker.
        
        Args:
            order_size: Size of the order in base currency
            spread: Current spread in quote currency
            volatility: Current volatility
            orderbook_imbalance: Current orderbook imbalance
            
        Returns:
            float: Estimated maker proportion (0.0 to 1.0)
        """
        if not self.is_fitted:
            # Fallback estimation if model not fitted
            return self._estimate_maker_proportion_fallback(order_size, spread, volatility, orderbook_imbalance)
            
        # Create feature vector
        X = np.array([[order_size, spread, volatility, orderbook_imbalance]])
        
        # Predict maker proportion
        return float(self.predict_proba(X)[0])
        
    def _estimate_maker_proportion_fallback(self, 
                                         order_size: float, 
                                         spread: float, 
                                         volatility: float, 
                                         orderbook_imbalance: float) -> float:
        """
        Fallback method to estimate maker proportion when model is not fitted.
        
        Args:
            order_size: Size of the order in base currency
            spread: Current spread in quote currency
            volatility: Current volatility
            orderbook_imbalance: Current orderbook imbalance
            
        Returns:
            float: Estimated maker proportion (0.0 to 1.0)
        """
        # Simple heuristic: maker proportion decreases with order size, volatility
        # and increases with spread and favorable orderbook imbalance
        
        # Base maker proportion
        base_proportion = 0.5
        
        # Adjust for order size (larger orders are more likely to be takers)
        size_factor = -0.1 * np.log1p(order_size) / 10.0  # Logarithmic scaling, capped at -0.1
        
        # Adjust for spread (wider spreads encourage maker orders)
        spread_factor = 0.1 * np.tanh(spread)  # Tanh to cap the effect
        
        # Adjust for volatility (higher volatility encourages taker orders)
        vol_factor = -0.2 * volatility
        
        # Adjust for orderbook imbalance
        # Positive imbalance (more bids than asks) encourages maker sells
        # Negative imbalance (more asks than bids) encourages maker buys
        imbalance_factor = 0.1 * orderbook_imbalance
        
        # Combine factors and clamp to [0, 1]
        maker_proportion = base_proportion + size_factor + spread_factor + vol_factor + imbalance_factor
        return max(0.0, min(1.0, maker_proportion))
