# Trade Simulator

A high-performance trade simulator leveraging real-time market data to estimate transaction costs and market impact for cryptocurrency exchanges.

## Features

- Real-time L2 orderbook data processing via WebSocket
- Slippage estimation using regression models
- Market impact calculation using Almgren-Chriss model
- Maker/Taker proportion prediction
- Fee calculation based on exchange fee tiers
- Interactive dashboard for visualization and simulation

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`
- VPN access to OKX (for accessing market data)

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd trade-simulator
```

2. Create a virtual environment and install dependencies:
```
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the application:
```
python src/main.py
```

Optional arguments:
- `--websocket-uri`: WebSocket URI for orderbook data (default: wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP)
- `--dashboard-port`: Port for the dashboard (default: 8050)

Once running, open your browser and navigate to:
```
http://localhost:8050
```

## Dashboard

The dashboard consists of:

- **Input Parameters**: Configure your simulation parameters
  - Exchange
  - Market Type (spot, futures)
  - Symbol
  - Order Side (buy, sell)
  - Quantity (in USD)
  - Volatility
  - Fee Tier

- **Simulation Results**: View the estimated costs
  - Expected Slippage
  - Expected Fees
  - Expected Market Impact
  - Net Cost
  - Maker/Taker Proportion
  - Internal Latency

- **Visualizations**:
  - Orderbook Visualization
  - Cost Breakdown

## Models

### Slippage Model

Estimates slippage based on order size, spread, volatility, and orderbook imbalance using linear or quantile regression.

### Market Impact Model

Implements the Almgren-Chriss model to calculate temporary and permanent market impact.

### Maker/Taker Model

Predicts the proportion of an order that will be executed as maker vs taker using logistic regression.

### Fee Model

Calculates trading fees based on exchange fee tiers, market type, and maker/taker proportion.

## Performance Optimization

- Efficient data structures for orderbook processing
- Optimized WebSocket client with automatic reconnection
- Performance metrics tracking (processing time per tick)
- Asynchronous processing for WebSocket data

## License

[MIT License](LICENSE)
