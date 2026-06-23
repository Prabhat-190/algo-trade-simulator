"""
Visualization module for the Almgren-Chriss model.

This module provides visualization tools to help understand the Almgren-Chriss model
for optimal trade execution, including:
- Optimal execution schedules
- Market impact visualization
- Risk-return trade-offs
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import Tuple, Dict, List, Optional
import pandas as pd

from src.models.market_impact import AlmgrenChrissModel


class AlmgrenChrissVisualizer:
    """
    Visualization tools for the Almgren-Chriss model.
    """
    
    def __init__(self, model: AlmgrenChrissModel):
        """
        Initialize the visualizer with an Almgren-Chriss model.
        
        Args:
            model: An instance of AlmgrenChrissModel
        """
        self.model = model
    
    def plot_optimal_execution(self, 
                              total_size: float, 
                              time_horizon: float, 
                              volatility: float,
                              title: str = "Optimal Execution Schedule") -> Figure:
        """
        Plot the optimal execution schedule based on the Almgren-Chriss model.
        
        Args:
            total_size: Total size of the order to execute
            time_horizon: Time horizon for execution (in hours)
            volatility: Market volatility
            title: Title for the plot
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Calculate optimal execution schedule
        times, trade_sizes = self.model.calculate_optimal_execution_schedule(
            total_size, time_horizon, volatility
        )
        
        # Calculate cumulative execution
        remaining_inventory = np.zeros_like(times)
        remaining_inventory[0] = total_size
        for i in range(1, len(times)):
            remaining_inventory[i] = remaining_inventory[i-1] - trade_sizes[i-1]
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Plot remaining inventory
        ax1.plot(times, remaining_inventory, 'b-', linewidth=2)
        ax1.set_ylabel('Remaining Inventory')
        ax1.set_title(title)
        ax1.grid(True)
        
        # Plot trade sizes
        ax2.bar(times, trade_sizes, width=time_horizon/len(times)*0.8, alpha=0.7)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Trade Size')
        ax2.grid(True)
        
        plt.tight_layout()
        return fig
    
    def compare_risk_aversion(self, 
                             total_size: float, 
                             time_horizon: float, 
                             volatility: float,
                             risk_aversions: List[float]) -> Figure:
        """
        Compare optimal execution schedules for different risk aversion parameters.
        
        Args:
            total_size: Total size of the order to execute
            time_horizon: Time horizon for execution (in hours)
            volatility: Market volatility
            risk_aversions: List of risk aversion parameters to compare
            
        Returns:
            Figure: Matplotlib figure object
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Store original risk aversion
        original_risk_aversion = self.model.risk_aversion
        
        # Calculate and plot for each risk aversion
        for risk_aversion in risk_aversions:
            # Temporarily set risk aversion
            self.model.risk_aversion = risk_aversion
            
            # Calculate optimal execution
            times, _ = self.model.calculate_optimal_execution_schedule(
                total_size, time_horizon, volatility
            )
            
            # Calculate remaining inventory
            remaining_inventory = np.zeros_like(times)
            remaining_inventory[0] = total_size
            for i in range(1, len(times)):
                remaining_inventory[i] = remaining_inventory[i-1] - _[i-1]
            
            # Plot
            ax.plot(times, remaining_inventory, linewidth=2, 
                   label=f'ψ = {risk_aversion}')
        
        # Restore original risk aversion
        self.model.risk_aversion = original_risk_aversion
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Remaining Inventory')
        ax.set_title('Effect of Risk Aversion on Execution Schedule')
        ax.grid(True)
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def visualize_market_impact(self,
                               order_sizes: List[float],
                               avg_daily_volume: float,
                               volatility: float,
                               mid_price: float,
                               orderbook_depth: float,
                               execution_time: float = 1.0) -> Figure:
        """
        Visualize market impact components for different order sizes.
        
        Args:
            order_sizes: List of order sizes to compare
            avg_daily_volume: Average daily trading volume
            volatility: Market volatility
            mid_price: Current mid price
            orderbook_depth: Depth of the orderbook
            execution_time: Time horizon for execution
            
        Returns:
            Figure: Matplotlib figure object
        """
        # Calculate impact for each order size
        impacts = []
        for size in order_sizes:
            impact = self.model.calculate_market_impact(
                size, avg_daily_volume, volatility, mid_price, 
                orderbook_depth, execution_time
            )
            impacts.append(impact)
        
        # Extract components
        temp_impacts = [impact['temporary_impact'] for impact in impacts]
        perm_impacts = [impact['permanent_impact'] for impact in impacts]
        exec_risks = [impact['execution_risk'] for impact in impacts]
        total_impacts = [impact['total_impact'] for impact in impacts]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot components
        width = 0.2
        x = np.arange(len(order_sizes))
        
        ax.bar(x - 1.5*width, temp_impacts, width, label='Temporary Impact')
        ax.bar(x - 0.5*width, perm_impacts, width, label='Permanent Impact')
        ax.bar(x + 0.5*width, exec_risks, width, label='Execution Risk')
        ax.bar(x + 1.5*width, total_impacts, width, label='Total Impact')
        
        ax.set_xlabel('Order Size')
        ax.set_ylabel('Impact (Price Units)')
        ax.set_title('Market Impact Components by Order Size')
        ax.set_xticks(x)
        ax.set_xticklabels([f'{size}' for size in order_sizes])
        ax.legend()
        
        plt.tight_layout()
        return fig


# Example usage
if __name__ == "__main__":
    # Create model and visualizer
    model = AlmgrenChrissModel(
        temporary_impact_factor=0.1,
        permanent_impact_factor=0.01,
        market_vol_factor=0.5,
        risk_aversion=0.001
    )
    visualizer = AlmgrenChrissVisualizer(model)
    
    # Plot optimal execution
    fig1 = visualizer.plot_optimal_execution(
        total_size=1000,
        time_horizon=4.0,
        volatility=0.3
    )
    
    # Compare risk aversions
    fig2 = visualizer.compare_risk_aversion(
        total_size=1000,
        time_horizon=4.0,
        volatility=0.3,
        risk_aversions=[0.0001, 0.001, 0.01, 0.1]
    )
    
    # Visualize market impact
    fig3 = visualizer.visualize_market_impact(
        order_sizes=[100, 500, 1000, 5000],
        avg_daily_volume=10000,
        volatility=0.3,
        mid_price=100.0,
        orderbook_depth=10000
    )
    
    plt.show()
