# Algo Trade Simulator

A production-ready, real-time algorithmic trading cost simulator built with Python, Dash, Plotly, WebSockets, Redis, Gunicorn, Nginx, and Docker. The app consumes live Level-2 order book data, stores the latest stream in Redis, and lets users simulate trade execution costs from a professional trading-terminal dashboard.

## What Is New

- **Production Hardening**: Redis connection resilience with retry logic, exponential backoff, and graceful degradation when Redis is unavailable
- **Improved Health Endpoint**: `/healthz` now reports Redis connectivity status, market data freshness, and detailed diagnostics
- **WebSocket Resilience**: Exponential backoff reconnection (5s → 10s → 20s → 40s → 60s max) with graceful shutdown handling
- **Docker Production Readiness**: Non-root user, health checks, proper signal handling, multi-stage build optimizations
- **Nginx Enhancements**: WebSocket forwarding, rate limiting, security headers, static asset caching, proper timeouts
- **Railway Deployment**: `railway.toml` configuration for easy Railway deployment
- **Professional UI/UX**: Obsidian glassmorphism theme, responsive design, mobile-first approach, improved visual hierarchy for key metrics
- **Import Path Fixes**: Proper Python package structure with `__init__.py` files, removed fragile `sys.path` manipulations

## Features

- Real-time WebSocket feed for OKX-compatible Level-2 order book data
- Redis Pub/Sub layer that separates market data ingestion from the dashboard
- Professional Dash dashboard with Plotly order book and cost breakdown charts
- Market order cost simulation for buy and sell orders
- Optional stock quote simulation for symbols such as AAPL, MSFT, TSLA, or NVDA
- Estimated slippage, fees, market impact, maker/taker mix, net cost, and internal latency
- Trading project save/load workflow for reusable simulation scenarios
- Gunicorn WSGI deployment with multiple workers and threads
- Nginx load balancer with WebSocket support and rate limiting
- Docker Compose stack with Redis, data feeder, dashboard, and load balancer
- Railway-ready deployment configuration
- Comprehensive test suite

## Project Structure

```text
algo-trade-simulator/
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── requirements.txt
├── README.md
├── .dockerignore
├── deploy/
│   └── nginx.conf
└── trading/
    ├── data_feeder.py
    ├── stock_data_feeder.py
    ├── src/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── data/
    │   │   ├── __init__.py
    │   │   ├── orderbook.py
    │   │   └── websocket_client.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── fee_model.py
    │   │   ├── maker_taker.py
    │   │   ├── market_impact.py
    │   │   ├── simulator.py
    │   │   ├── slippage_model.py
    │   │   └── trading_project.py
    │   ├── ui/
    │   │   ├── __init__.py
    │   │   └── dashboard.py
    │   └── visualization/
    │       ├── __init__.py
    │       └── almgren_chriss_visualizer.py
    └── tests/
        ├── __init__.py
        ├── test_simulator.py
        ├── test_stock_data_feeder.py
        └── test_trading_project.py
```

## Architecture

```text
OKX / WebSocket Feed
        |
        v
trading/data_feeder.py (with reconnection & Redis resilience)
        |
        v
Redis Pub/Sub + Redis Hash Storage (with connection pooling & health checks)
        |
        v
Dash Application + TradeSimulator (with graceful Redis degradation)
        |
        v
Gunicorn Workers (multi-process, multi-thread)
        |
        v
Nginx Load Balancer (WebSocket support, rate limiting, security headers)
        |
        v
Browser Dashboard (Professional trading terminal UI)
```

### Runtime Flow

1. `data_feeder.py` connects to the WebSocket market data feed with exponential backoff reconnection
2. The feeder publishes order book frames to Redis channels named `orderbook:<symbol>:stream`
3. `trading/src/main.py` starts the Dash app and subscribes to Redis in a background thread with connection resilience
4. `TradeSimulator` updates the internal order book and calculates cost estimates
5. `Dashboard` displays order book charts, cost charts, connection status, and trading project controls
6. Gunicorn serves the Flask server exposed by Dash with multiple workers/threads
7. Nginx routes browser traffic to the dashboard service and provides the load-balancing layer

## Trading Project Feature

The Trading Project panel lets users save a reusable simulation setup.

Saved fields:
- Project name
- Strategy type
- Exchange
- Market type
- Symbol
- Buy/sell side
- Quantity in USD
- Volatility assumption
- Fee tier

When Redis is available, projects are stored in a Redis hash named `trading_projects`. This matters for load balancing because multiple Gunicorn workers and replicated dashboard containers can read the same saved setups. When Redis is unavailable, projects fall back to in-memory storage.

## Load Balancing Feature

The root `docker-compose.yml` adds a `load_balancer` service using Nginx. Nginx forwards traffic to `web_dashboard:7860`. Gunicorn also runs multiple workers and threads inside the dashboard container.

Default settings:
```
WEB_CONCURRENCY=2
GUNICORN_THREADS=4
PORT=7860
```

Run multiple dashboard containers with:
```bash
docker compose up --build --scale web_dashboard=3
```

Then open:
```
http://localhost:7860
```

## Local Setup Without Docker

```bash
cd /path/to/algo-trade-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start Redis separately, then run the feeder and dashboard in two terminals.

Terminal 1:
```bash
redis-server
```

Terminal 2:
```bash
source .venv/bin/activate
REDIS_HOST=localhost python trading/data_feeder.py
```

Terminal 3:
```bash
source .venv/bin/activate
REDIS_HOST=localhost python trading/src/main.py --port 8050
```

Open:
```
http://localhost:8050
```

## Docker Deployment

### Prerequisites

If your terminal shows:
```
zsh: command not found: docker
```
then Docker is not installed, Docker Desktop is not running, or the Docker CLI is not available in your shell `PATH`.

Fix on macOS:
1. Install Docker Desktop from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Open Docker Desktop once and wait until it says Docker is running
3. Close and reopen Terminal
4. Check:
```bash
docker --version
docker compose version
```

### Running with Docker Compose

From the project root:
```bash
cd /path/to/algo-trade-simulator
docker compose up --build
```

Open:
```
http://localhost:7860
```

Health check:
```bash
curl http://localhost:7860/healthz
```

Scale dashboard replicas:
```bash
docker compose up --build --scale web_dashboard=3
```

Stop containers:
```bash
docker compose down
```

### Docker Image Details

The Dockerfile uses:
- Python 3.11 slim base image
- Non-root user for security
- Health check endpoint at `/healthz`
- Gunicorn with gthread workers for concurrent request handling
- Proper signal handling for graceful shutdown

## Stock Quote Mode From Free Sources

True real-time stock Level-2 order-book data is usually paid and exchange-licensed. This project includes a free-source stock quote mode that polls a free quote API and converts the current stock price into a synthetic order book. That lets the simulator estimate stock trade costs using the existing slippage, fee, and impact pipeline.

Supported providers:
- Finnhub quote API: [https://finnhub.io/docs/api/quote](https://finnhub.io/docs/api/quote)
- Alpha Vantage Global Quote API: [https://www.alphavantage.co/documentation/](https://www.alphavantage.co/documentation/)

### Run Stock Mode With Docker

Create a free Finnhub API key, then run:
```bash
cd /path/to/algo-trade-simulator
export FINNHUB_API_KEY=your_finnhub_key
export STOCK_SYMBOL=AAPL
docker compose --profile stocks up --build
```

Open:
```
http://localhost:7860
```

To use Alpha Vantage instead:
```bash
export STOCK_PROVIDER=alphavantage
export ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
export STOCK_SYMBOL=MSFT
docker compose --profile stocks up --build
```

### Run Stock Mode Without Docker

Start Redis, then run the stock feeder and dashboard in separate terminals:
```bash
source .venv/bin/activate
export FINNHUB_API_KEY=your_finnhub_key
export STOCK_SYMBOL=AAPL
REDIS_HOST=localhost python trading/stock_data_feeder.py
```

```bash
source .venv/bin/activate
REDIS_HOST=localhost python trading/src/main.py --port 8050
```

Open:
```
http://localhost:8050
```

**Important**: Because free quote APIs do not provide full market depth, `stock_data_feeder.py` creates a synthetic order book around the latest quote. Use it for learning, demos, and cost-estimation experiments, not for live trading decisions.

## Railway Deployment

This project includes a `railway.toml` configuration for easy deployment on Railway.

### Railway Setup

1. Create a new Railway project
2. Add a Redis service (Railway provides managed Redis)
3. Add the following services using the Dockerfile:

**Web Dashboard Service:**
- Build: Dockerfile
- Variables:
  - `PORT=7860`
  - `WEB_CONCURRENCY=2`
  - `GUNICORN_THREADS=4`
  - `REDIS_HOST=${{REDIS_HOST}}`
  - `REDIS_PORT=${{REDIS_PORT}}`
  - `MODELS_DIR=/app/models`

**Data Feeder Service:**
- Build: Dockerfile
- Command: `python trading/data_feeder.py`
- Variables:
  - `REDIS_HOST=${{REDIS_HOST}}`
  - `REDIS_PORT=${{REDIS_PORT}}`
  - `WEBSOCKET_URI=${{WEBSOCKET_URI}}`

**Stock Data Feeder Service (optional):**
- Build: Dockerfile
- Command: `python trading/stock_data_feeder.py`
- Variables:
  - `REDIS_HOST=${{REDIS_HOST}}`
  - `REDIS_PORT=${{REDIS_PORT}}`
  - `STOCK_SYMBOL=${{STOCK_SYMBOL:-AAPL}}`
  - `STOCK_PROVIDER=${{STOCK_PROVIDER:-finnhub}}`
  - `STOCK_POLL_INTERVAL=${{STOCK_POLL_INTERVAL:-15}}`
  - `FINNHUB_API_KEY=${{FINNHUB_API_KEY}}`
  - `ALPHA_VANTAGE_API_KEY=${{ALPHA_VANTAGE_API_KEY}}`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `PORT` | Dashboard port | `7860` |
| `WEB_CONCURRENCY` | Gunicorn worker count | `2` |
| `GUNICORN_THREADS` | Threads per worker | `4` |
| `WEBSOCKET_URI` | OKX WebSocket endpoint | `wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP` |
| `MODELS_DIR` | Directory for ML model weights | `None` |
| `STOCK_SYMBOL` | Stock symbol for stock mode | `AAPL` |
| `STOCK_PROVIDER` | Stock quote provider (finnhub/alphavantage) | `finnhub` |
| `STOCK_POLL_INTERVAL` | Poll interval in seconds | `15` |
| `FINNHUB_API_KEY` | Finnhub API key | Required for stock mode |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | Required for alphavantage provider |

## Render / Fly.io Deployment Notes

For platforms that support multiple services, create these services:
- Redis service
- Web service from this Dockerfile
- Worker service running `python trading/data_feeder.py`

Environment variables for the web service and worker:
```
REDIS_HOST=<your redis host>
REDIS_PORT=6379
PORT=7860
WEB_CONCURRENCY=2
GUNICORN_THREADS=4
WEBSOCKET_URI=wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP
```

Start command for web service:
```bash
gunicorn -b 0.0.0.0:$PORT --workers $WEB_CONCURRENCY --worker-class gthread --threads $GUNICORN_THREADS --timeout 120 src.main:server
```

Start command for worker service:
```bash
python trading/data_feeder.py
```

## Testing

```bash
cd trading
python -m pytest tests/ -v
```

Expected result:
```
============================= test session starts ==============================
collected 6 items

tests/test_simulator.py::TestSimulator::test_orderbook_methods PASSED
tests/test_simulator.py::TestSimulator::test_simulate_market_order PASSED
tests/test_simulator.py::TestSimulator::test_update_orderbook PASSED
tests/test_stock_data_feeder.py::TestStockQuoteFeeder::test_build_synthetic_orderbook PASSED
tests/test_trading_project.py::TestTradingProjectStore::test_project_options_are_dropdown_ready PASSED
tests/test_trading_project.py::TestTradingProjectStore::test_save_and_load_project_from_memory PASSED

============================== 6 passed in 2.00s ===============================
```

## Financial Models

### Slippage Model
- Uses linear or quantile regression when trained
- Fallback: heuristic based on spread, order size, volatility, and orderbook imbalance

### Market Impact Model (Almgren-Chriss)
- Temporary impact: immediate price change due to the trade
- Permanent impact: lasting price change after the trade
- Execution risk: price volatility during execution
- Orderbook depth adjustment

### Maker/Taker Model
- Logistic regression when trained
- Fallback: heuristic based on order size, spread, volatility, and orderbook imbalance

### Fee Model
- Exchange-specific fee tiers (OKX spot/futures VIP0-VIP5)
- Maker/taker fee calculation with proportion estimation

### Net Cost Calculation
```
net_cost = fees + slippage + market_impact
net_cost_percentage = (net_cost / order_value) * 100
```

## Important Terms

- **Algorithmic trading**: Using software rules or models to analyze and execute trades
- **Trade simulator**: Tool that estimates trade execution behavior without placing real orders
- **Order book**: Live list of buy and sell orders available in a market
- **Level-2 data**: Detailed order book data containing multiple bid and ask price levels
- **Bid**: Highest price buyers are currently willing to pay
- **Ask**: Lowest price sellers are currently willing to accept
- **Spread**: Difference between the best ask and best bid
- **Mid price**: Average of the best bid and best ask
- **Market order**: Order that executes immediately against available liquidity
- **Slippage**: Difference between expected execution price and actual/estimated execution price
- **Market impact**: Price movement caused by placing a trade, especially a large trade
- **Fees**: Exchange charges paid for trade execution
- **Maker**: Trader/order that adds liquidity to the order book
- **Taker**: Trader/order that removes liquidity from the order book
- **Maker/taker proportion**: Estimated split between liquidity-adding and liquidity-removing behavior
- **Volatility**: Measure of how much the asset price moves over time
- **Liquidity**: How easily an asset can be bought or sold without moving the price too much
- **Order book imbalance**: Difference between bid and ask volume, normalized by total volume
- **Net cost**: Total estimated execution cost including fees, slippage, and market impact
- **Redis**: In-memory data store used here for Pub/Sub and saved trading projects
- **Pub/Sub**: Publish/subscribe messaging where one service publishes data and others consume it
- **WebSocket**: Persistent network connection used for real-time streaming data
- **Dash**: Python framework for building interactive dashboards
- **Plotly**: Charting library used by Dash for visualizations
- **Flask**: Web server framework underneath Dash
- **Gunicorn**: Production Python WSGI server used to run the Dash/Flask app
- **Worker**: Gunicorn process that handles web requests
- **Thread**: Lightweight execution unit inside a worker
- **Load balancer**: Service that distributes incoming traffic across app instances
- **Nginx**: Reverse proxy used here as the load balancer
- **Health check**: Endpoint or command used to confirm a service is alive
- **Docker**: Container runtime used to package and run the app consistently
- **Docker Compose**: Tool for running multiple Docker services together
- **WSGI**: Python web server interface used by Gunicorn to serve Flask/Dash
- **Environment variable**: Runtime configuration passed outside the code
- **Stock quote**: Latest reported price information for a stock symbol
- **Synthetic order book**: Estimated bid/ask depth generated from quote data when real Level-2 stock data is unavailable
- **API key**: Secret token used to access a third-party data provider

## Common Deployment Problems And Fixes

- `zsh: command not found: docker`: Install Docker Desktop, open it once, reopen Terminal, then run `docker --version`
- `ModuleNotFoundError: No module named src`: Run from the project root and use `src.main:server` for Gunicorn
- Dashboard opens but says `Not connected`: Redis or the data feeder is not running, or `REDIS_HOST` is wrong
- Docker Compose does not work: Install Docker Desktop first and make sure `docker compose version` works
- Hugging Face build fails with Compose: Hugging Face Spaces expects a single Dockerfile container, not a multi-service compose stack
- No market data appears: Check `WEBSOCKET_URI` and whether your network can reach the WebSocket endpoint
- Stock mode logs `API key is required`: Create a free Finnhub or Alpha Vantage key and export it before starting the stock feeder
- Health check returns Redis error: Ensure Redis is running and accessible at `REDIS_HOST:REDIS_PORT`
- WebSocket reconnection storms: The client uses exponential backoff (5s → 10s → 20s → 40s → 60s max) with jitter

## Security

- Non-root user in Docker container
- Security headers in Nginx (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy)
- Rate limiting on API and dashboard endpoints
- No secrets in code - all configuration via environment variables
- Redis connections with timeouts and health checks

## License

Add your preferred license before publishing the project publicly.