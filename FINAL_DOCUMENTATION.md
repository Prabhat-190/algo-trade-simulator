# Final Project Documentation: Algo Trade Simulator

## Project Summary

Algo Trade Simulator is a real-time dashboard that estimates the cost of executing a crypto or stock trade. It receives crypto Level-2 order book data through a WebSocket feed, or free stock quote data through a quote API, forwards the data through Redis, and displays trading cost analytics in a Dash web app.

The improved version adds three important features: load-balanced deployment, saved Trading Projects, and a free-source stock quote mode.

## Main Modules

- `trading/data_feeder.py`: connects to the WebSocket feed and publishes market data into Redis.
- `trading/stock_data_feeder.py`: polls a free stock quote API and converts the quote into a synthetic order book for the simulator.
- `trading/src/main.py`: starts the Dash application, subscribes to Redis, exposes `/healthz`, and exposes `server` for Gunicorn.
- `trading/src/ui/dashboard.py`: builds the dashboard UI and callback logic.
- `trading/src/models/simulator.py`: calculates slippage, fees, market impact, net cost, and latency.
- `trading/src/models/trading_project.py`: stores saved trading projects in Redis with an in-memory fallback.
- `deploy/nginx.conf`: reverse proxy and load balancer configuration.
- `docker-compose.yml`: production-style multi-service stack.

## New Feature 1: Trading Projects

The dashboard now includes a Trading Project panel. A user can save a complete trading setup and load it again later.

A Trading Project stores:

- Project name
- Strategy
- Exchange
- Market type
- Symbol
- Order side
- Quantity in USD
- Volatility
- Fee tier

Redis is used for project storage when available, so the feature continues to work when the dashboard runs with multiple workers or replicas.

## New Feature 2: Stock Quote Mode

The project can now run with stock symbols such as `AAPL`, `MSFT`, `TSLA`, or `NVDA`.

Free stock APIs usually provide quote data, not full exchange Level-2 order-book depth. Because the simulator expects bids and asks, `trading/stock_data_feeder.py` converts the latest stock quote into a synthetic order book around the current price. This is useful for learning, demos, and cost-estimation experiments, but it should not be used as a live trading decision engine.

Supported free-source references:

- Finnhub quote API: https://finnhub.io/docs/api/quote
- Alpha Vantage Global Quote API: https://www.alphavantage.co/documentation/

Run stock mode with Docker:

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
export FINNHUB_API_KEY=your_finnhub_key
export STOCK_SYMBOL=AAPL
docker compose --profile stocks up --build
```

Run stock mode without Docker:

```bash
export FINNHUB_API_KEY=your_finnhub_key
export STOCK_SYMBOL=AAPL
REDIS_HOST=localhost python trading/stock_data_feeder.py
```

Then start the dashboard:

```bash
REDIS_HOST=localhost python trading/src/main.py --port 8050
```

## New Feature 3: Load Balancing

The deployment now includes Nginx as a load balancer and Gunicorn as the production WSGI server.

The request path is:

```text
Browser -> Nginx -> Gunicorn -> Dash/Flask -> TradeSimulator
```

The data path is:

```text
WebSocket Feed -> Data Feeder -> Redis -> Dashboard Subscriber -> Simulator
```

To scale dashboard containers:

```bash
docker compose up --build --scale web_dashboard=3
```

Open the app at:

```text
http://localhost:7860
```

## Deployment Fixes Made

- Fixed Gunicorn app target from the wrong module path to `trading.src.main:server`.
- Fixed Python import path setup in `trading/src/main.py`.
- Added root-level `docker-compose.yml` with Redis, feeder, dashboard, and Nginx.
- Added `/healthz` endpoint for health checks.
- Added Docker health checks for Redis and the dashboard.
- Added `.dockerignore` to keep Docker builds cleaner.

## How To Run Locally With Docker

If this command fails with `zsh: command not found: docker`, Docker is not installed or not available in your terminal. Install Docker Desktop from https://www.docker.com/products/docker-desktop/, open Docker Desktop once, wait until it is running, then reopen Terminal and check:

```bash
docker --version
docker compose version
```

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
docker compose up --build
```

Open:

```text
http://localhost:7860
```

Check health:

```bash
curl http://localhost:7860/healthz
```

Stop:

```bash
docker compose down
```

## How To Run Locally Without Docker

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start Redis:

```bash
redis-server
```

Start data feeder:

```bash
REDIS_HOST=localhost python trading/data_feeder.py
```

Start dashboard:

```bash
REDIS_HOST=localhost python trading/src/main.py --port 8050
```

Open:

```text
http://localhost:8050
```

## Terms For Explanation

- Order book: list of buy and sell orders in a market.
- Level-2 data: order book data with multiple price levels.
- Bid: price buyers are willing to pay.
- Ask: price sellers are willing to accept.
- Spread: ask price minus bid price.
- Mid price: average of best bid and best ask.
- Slippage: difference between expected and estimated execution price.
- Market impact: price effect caused by the trade itself.
- Fee tier: exchange pricing level that affects trading fees.
- Maker: order that adds liquidity.
- Taker: order that removes liquidity.
- Liquidity: available market depth for buying or selling.
- Redis: in-memory store used for messaging and saved projects.
- WebSocket: real-time streaming connection.
- Dash: Python dashboard framework.
- Gunicorn: production web server for Python web apps.
- Nginx: reverse proxy and load balancer.
- Docker Compose: multi-container deployment tool.
- Health check: endpoint used to confirm the app is running.
- Stock quote: latest available stock price from a quote API.
- Synthetic order book: generated bid/ask levels based on quote data when real Level-2 stock depth is unavailable.
- API key: secret token used to access a third-party data provider.

## Verification Completed

I ran:

```bash
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m py_compile trading/src/main.py trading/src/ui/dashboard.py trading/src/models/trading_project.py trading/data_feeder.py trading/stock_data_feeder.py
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m unittest discover trading/tests
```

Result:

```text
Ran 6 tests
OK
```

Docker could not be executed in this Codex shell because the `docker` command is not installed or not available in PATH. The compose file and Dockerfile have been updated, but you should run `docker compose up --build` on a machine with Docker Desktop installed.
