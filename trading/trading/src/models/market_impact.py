"""
Market impact model based on Almgren-Chriss model.
"""
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

class AlmgrenChrissModel:
    """
    Implementation of the Almgren-Chriss model for market impact.

    The model divides market impact into:
    1. Temporary impact: immediate price change due to the trade (γ×t)
    2. Permanent impact: lasting price change that remains after the trade (η×X)

    The model also considers execution risk from price volatility during execution.

    References:
    - Almgren, R., & Chriss, N. (2001). Optimal execution of portfolio transactions.
    """
    def __init__(self,
                 temporary_impact_factor: float = 0.1,
                 permanent_impact_factor: float = 0.01,
                 market_vol_factor: float = 0.5,
                 risk_aversion: float = 0.001):
        """
        Initialize the Almgren-Chriss market impact model.

        Args:
            temporary_impact_factor: Factor γ for temporary impact calculation
            permanent_impact_factor: Factor η for permanent impact calculation
            market_vol_factor: Factor for incorporating market volatility
            risk_aversion: Risk aversion parameter ψ that reflects trader's tolerance for execution risk
        """
        self.temporary_impact_factor = temporary_impact_factor
        self.permanent_impact_factor = permanent_impact_factor
        self.market_vol_factor = market_vol_factor
        self.risk_aversion = risk_aversion

    def calculate_market_impact(self,
                               order_size: float,
                               avg_daily_volume: float,
                               volatility: float,
                               mid_price: float,
                               orderbook_depth: float,
                               execution_time: float = 1.0) -> Dict[str, float]:
        """
        Calculate market impact for a market order using the Almgren-Chriss model.

        Args:
            order_size: Size of the order in base currency
            avg_daily_volume: Average daily trading volume
            volatility: Current market volatility
            mid_price: Current mid price
            orderbook_depth: Depth of the orderbook (sum of quantities)
            execution_time: Time horizon for execution (in hours)

        Returns:
            Dict: Dictionary with temporary, permanent, execution risk, and total impact
        """
        # We'll use the normalized order size for additional adjustments
        # This helps account for the relative size of the order compared to typical volume
        normalized_size = order_size / avg_daily_volume if avg_daily_volume > 0 else 0

        # Calculate temporary impact (immediate price change)
        # Temporary impact formula: γ × t (where t is trading rate)
        trading_rate = order_size / execution_time

        # Apply a scaling factor based on normalized size
        size_scaling = np.sqrt(normalized_size) if normalized_size > 0 else 1.0

        temporary_impact = (
            self.temporary_impact_factor *
            mid_price *
            trading_rate *
            size_scaling *
            (1 + self.market_vol_factor * volatility)
        )

        # Calculate permanent impact (lasting price change)
        # Permanent impact formula: η × X (where X is total order size)
        permanent_impact = (
            self.permanent_impact_factor *
            mid_price *
            order_size
        )

        # Calculate execution risk
        # Execution risk formula: 0.5 × ψ × σ² × T × X²
        execution_risk = (
            0.5 *
            self.risk_aversion *
            (volatility ** 2) *
            execution_time *
            (order_size ** 2)
        )

        # Adjust for orderbook depth
        # Deeper orderbooks reduce market impact
        depth_adjustment = 1.0
        if orderbook_depth > 0:
            depth_ratio = order_size / orderbook_depth
            depth_adjustment = 1.0 + np.tanh(depth_ratio)  # Smooth function that approaches 2 for large orders

        temporary_impact *= depth_adjustment

        # Total impact is the sum of temporary and permanent impacts plus execution risk
        total_impact = temporary_impact + permanent_impact + execution_risk

        return {
            'temporary_impact': temporary_impact,
            'permanent_impact': permanent_impact,
            'execution_risk': execution_risk,
            'total_impact': total_impact
        }

    def calculate_optimal_execution_schedule(self,
                                           total_size: float,
                                           time_horizon: float,
                                           volatility: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate optimal execution schedule based on Almgren-Chriss model.

        Args:
            total_size: Total size of the order to execute
            time_horizon: Time horizon for execution (in hours)
            volatility: Market volatility

        Returns:
            Tuple[np.ndarray, np.ndarray]: (times, sizes) for execution schedule
        """
        # Number of trading intervals
        n_intervals = max(int(time_horizon * 4), 2)  # At least 2 intervals, default to 4 per hour

        # Time points
        times = np.linspace(0, time_horizon, n_intervals)

        # Use the risk aversion parameter from the model
        risk_aversion = self.risk_aversion

        # Parameters from the Almgren-Chriss model
        gamma = self.temporary_impact_factor  # Temporary impact factor

        # Calculate optimal trading trajectory
        # For risk-averse traders (high risk_aversion), execution is faster at the beginning
        # For risk-neutral traders (low risk_aversion), execution is more evenly distributed

        # Almgren-Chriss formula for optimal trading trajectory
        alpha = risk_aversion * volatility**2

        # Calculate the optimal trading trajectory using the Almgren-Chriss formula
        # For a liquidation problem, we start with X shares and end with 0

        # Initialize arrays for remaining inventory and trade sizes
        remaining_sizes = np.zeros(n_intervals)
        trade_sizes = np.zeros(n_intervals)

        if alpha == 0:
            # Risk-neutral case: linear trading (equal-sized trades)
            trade_per_step = total_size / (n_intervals - 1)
            for i in range(n_intervals - 1):
                trade_sizes[i] = trade_per_step

            # Calculate remaining inventory
            remaining_sizes[0] = total_size
            for i in range(1, n_intervals):
                remaining_sizes[i] = remaining_sizes[i-1] - trade_sizes[i-1]
        else:
            # Risk-averse case: using the analytical solution from Almgren-Chriss
            # The solution gives a trading trajectory that decays exponentially

            # Calculate the optimal trading trajectory
            sinh_term = np.sinh(np.sqrt(alpha * gamma) * time_horizon)

            # Set initial inventory
            remaining_sizes[0] = total_size

            # Calculate remaining inventory at each time point
            for i in range(1, n_intervals):
                t = times[i]
                # Formula from Almgren-Chriss paper
                remaining_factor = np.sinh(np.sqrt(alpha * gamma) * (time_horizon - t)) / sinh_term
                remaining_sizes[i] = total_size * remaining_factor

            # Calculate trade sizes from the changes in remaining inventory
            for i in range(n_intervals - 1):
                trade_sizes[i] = remaining_sizes[i] - remaining_sizes[i+1]

            # Ensure the last trade completes the order
            trade_sizes[-1] = remaining_sizes[-1]

        # Ensure we're trading the exact total size by adjusting the final trade
        if np.abs(np.sum(trade_sizes) - total_size) > 1e-10:
            trade_sizes[-1] += (total_size - np.sum(trade_sizes))

        return times, trade_sizes
