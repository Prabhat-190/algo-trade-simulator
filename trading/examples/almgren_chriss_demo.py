"""
Demonstration of the Almgren-Chriss model for optimal trade execution.

This script demonstrates:
1. How to use the Almgren-Chriss model for calculating market impact
2. How to generate optimal execution schedules
3. How to visualize the results
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.market_impact import AlmgrenChrissModel
from src.visualization.almgren_chriss_visualizer import AlmgrenChrissVisualizer


def demo_market_impact():
    """
    Demonstrate market impact calculations using the Almgren-Chriss model.
    """
    print("\n=== Market Impact Demonstration ===")
    
    # Create model with default parameters
    model = AlmgrenChrissModel(
        temporary_impact_factor=0.1,
        permanent_impact_factor=0.01,
        market_vol_factor=0.5,
        risk_aversion=0.001
    )
    
    # Example market conditions
    order_size = 1000  # units
    avg_daily_volume = 10000  # units
    volatility = 0.3  # 30% annualized volatility
    mid_price = 100.0  # price units
    orderbook_depth = 5000  # units
    execution_time = 2.0  # hours
    
    # Calculate market impact
    impact = model.calculate_market_impact(
        order_size, avg_daily_volume, volatility, 
        mid_price, orderbook_depth, execution_time
    )
    
    # Print results
    print(f"Order Size: {order_size} units")
    print(f"Mid Price: ${mid_price:.2f}")
    print(f"Execution Time: {execution_time} hours")
    print(f"Temporary Impact: ${impact['temporary_impact']:.4f}")
    print(f"Permanent Impact: ${impact['permanent_impact']:.4f}")
    print(f"Execution Risk: ${impact['execution_risk']:.4f}")
    print(f"Total Impact: ${impact['total_impact']:.4f}")
    print(f"Impact as % of order value: {100 * impact['total_impact'] / (order_size * mid_price):.4f}%")


def demo_optimal_execution():
    """
    Demonstrate optimal execution schedule calculation.
    """
    print("\n=== Optimal Execution Demonstration ===")
    
    # Create model with default parameters
    model = AlmgrenChrissModel(
        temporary_impact_factor=0.1,
        permanent_impact_factor=0.01,
        market_vol_factor=0.5,
        risk_aversion=0.001
    )
    
    # Example parameters
    total_size = 1000  # units
    time_horizon = 4.0  # hours
    volatility = 0.3  # 30% annualized volatility
    
    # Calculate optimal execution schedule
    times, trade_sizes = model.calculate_optimal_execution_schedule(
        total_size, time_horizon, volatility
    )
    
    # Print results
    print(f"Total Order Size: {total_size} units")
    print(f"Time Horizon: {time_horizon} hours")
    print(f"Number of Trading Intervals: {len(times)}")
    
    print("\nOptimal Execution Schedule:")
    print("Time (hours) | Trade Size (units)")
    print("-" * 30)
    
    for i in range(len(times)):
        print(f"{times[i]:.2f} | {trade_sizes[i]:.2f}")
    
    print(f"\nTotal Executed: {np.sum(trade_sizes):.2f} units")


def demo_visualization():
    """
    Demonstrate visualization of the Almgren-Chriss model.
    """
    print("\n=== Visualization Demonstration ===")
    
    # Create model and visualizer
    model = AlmgrenChrissModel(
        temporary_impact_factor=0.1,
        permanent_impact_factor=0.01,
        market_vol_factor=0.5,
        risk_aversion=0.001
    )
    visualizer = AlmgrenChrissVisualizer(model)
    
    # Example parameters
    total_size = 1000  # units
    time_horizon = 4.0  # hours
    volatility = 0.3  # 30% annualized volatility
    
    # Plot optimal execution
    print("Plotting optimal execution schedule...")
    fig1 = visualizer.plot_optimal_execution(
        total_size=total_size,
        time_horizon=time_horizon,
        volatility=volatility,
        title="Optimal Execution Schedule (ψ=0.001)"
    )
    
    # Compare risk aversions
    print("Comparing different risk aversion parameters...")
    fig2 = visualizer.compare_risk_aversion(
        total_size=total_size,
        time_horizon=time_horizon,
        volatility=volatility,
        risk_aversions=[0.0001, 0.001, 0.01, 0.1]
    )
    
    # Visualize market impact
    print("Visualizing market impact components...")
    fig3 = visualizer.visualize_market_impact(
        order_sizes=[100, 500, 1000, 5000],
        avg_daily_volume=10000,
        volatility=volatility,
        mid_price=100.0,
        orderbook_depth=5000
    )
    
    # Show all figures
    plt.show()


def demo_risk_sensitivity():
    """
    Demonstrate sensitivity to risk aversion and volatility.
    """
    print("\n=== Risk Sensitivity Demonstration ===")
    
    # Create model
    model = AlmgrenChrissModel(
        temporary_impact_factor=0.1,
        permanent_impact_factor=0.01,
        market_vol_factor=0.5,
        risk_aversion=0.001
    )
    
    # Example parameters
    total_size = 1000  # units
    time_horizon = 4.0  # hours
    base_volatility = 0.3  # 30% annualized volatility
    
    # Test different volatilities
    volatilities = [0.1, 0.3, 0.5, 0.7]
    
    print("Effect of Volatility on Execution Risk:")
    print("Volatility | Execution Risk ($)")
    print("-" * 30)
    
    for vol in volatilities:
        # Calculate market impact with different volatilities
        impact = model.calculate_market_impact(
            total_size, 10000, vol, 100.0, 5000, time_horizon
        )
        print(f"{vol:.1f} | {impact['execution_risk']:.2f}")


if __name__ == "__main__":
    print("Almgren-Chriss Model Demonstration")
    print("==================================")
    
    # Run demonstrations
    demo_market_impact()
    demo_optimal_execution()
    demo_risk_sensitivity()
    
    # Run visualization (commented out by default)
    # Uncomment to show plots
    demo_visualization()
