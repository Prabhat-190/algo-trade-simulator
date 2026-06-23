# Algo Trade Simulator

A real-time algorithmic trading cost simulator built with Python, Dash, Plotly, WebSockets, Redis, Gunicorn, and Docker. The app consumes live Level-2 order book data, stores the latest stream in Redis, and lets users simulate trade execution cost from a web dashboard.

## What Is New

- Load-balanced deployment: the app now runs behind an Nginx reverse proxy and can scale Dash/Gunicorn workers with Docker Compose.
- Health endpoint: `/healthz` is available for Docker health checks and cloud deployment probes.
- Trading Project feature: users can save and reload reusable trading setups such as symbol, side, strategy, quantity, volatility, and fee tier.
- Stock quote feeder: optional free stock-source mode using Finnhub or Alpha Vantage quote APIs, converted into a simulator-compatible synthetic order book.
- Redis-backed project storage: saved trading projects are shared across Gunicorn workers and scaled dashboard replicas.
- Fixed deployment paths: Gunicorn now points to the real WSGI app at `trading.src.main:server`.
- Better deployment documentation: local, Docker, scaled Docker, and cloud deployment steps are included below.

## Features

- Real-time WebSocket feed for OKX-compatible Level-2 order book data.
- Redis Pub/Sub layer that separates market data ingestion from the dashboard.
- Dash dashboard with Plotly order book and cost breakdown charts.
- Market order cost simulation for buy and sell orders.
- Optional stock quote simulation for symbols such as AAPL, MSFT, TSLA, or NVDA.
- Estimated slippage, fees, market impact, maker/taker mix, net cost, and internal latency.
- Trading project save/load workflow for reusable simulation scenarios.
- Gunicorn WSGI deployment support.
- Nginx load balancer configuration.
- Docker Compose stack with Redis, data feeder, dashboard, and load balancer.

## Project Structure

```text
algo-trade-simulator-main/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
├── deploy/
│   └── nginx.conf
└── trading/
    ├── data_feeder.py
    ├── docker-compose.yml
    ├── examples/
    │   └── almgren_chriss_demo.py
    ├── src/
    │   ├── main.py
    │   ├── data/
    │   │   ├── orderbook.py
    │   │   └── websocket_client.py
    │   ├── models/
    │   │   ├── fee_model.py
    │   │   ├── maker_taker.py
    │   │   ├── market_impact.py
    │   │   ├── simulator.py
    │   │   ├── slippage_model.py
    │   │   └── trading_project.py
    │   ├── ui/
    │   │   └── dashboard.py
    │   └── visualization/
    │       └── almgren_chriss_visualizer.py
    └── tests/
        ├── test_simulator.py
        └── test_trading_project.py
```

## Architecture

```text
OKX / WebSocket Feed
        |
        v
trading/data_feeder.py
        |
        v
Redis Pub/Sub + Redis Hash Storage
        |
        v
Dash Application + TradeSimulator
        |
        v
Gunicorn Workers
        |
        v
Nginx Load Balancer
        |
        v
Browser Dashboard
```

### Runtime Flow

1. `data_feeder.py` connects to the WebSocket market data feed.
2. The feeder publishes order book frames to Redis channels named `orderbook:<symbol>:stream`.
3. `trading/src/main.py` starts the Dash app and subscribes to Redis in a background thread.
4. `TradeSimulator` updates the internal order book and calculates cost estimates.
5. `Dashboard` displays order book charts, cost charts, connection status, and trading project controls.
6. Gunicorn serves the Flask server exposed by Dash.
7. Nginx routes browser traffic to the dashboard service and provides the load-balancing layer.

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

When Redis is available, projects are stored in a Redis hash named `trading_projects`. This matters for load balancing because multiple Gunicorn workers and replicated dashboard containers can read the same saved setups.

## Load Balancing Feature

The root `docker-compose.yml` adds a `load_balancer` service using Nginx. Nginx forwards traffic to `web_dashboard:7860`. Gunicorn also runs multiple workers and threads inside the dashboard container.

Default settings:

```text
WEB_CONCURRENCY=2
GUNICORN_THREADS=4
PORT=7860
```

Run multiple dashboard containers with:

```bash
docker compose up --build --scale web_dashboard=3
```

Then open:

```text
http://localhost:7860
```

## Local Setup Without Docker

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
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

```text
http://localhost:8050
```

## Docker Deployment

### Why `docker: command not found` Happens

If your terminal shows:

```text
zsh: command not found: docker
```

then Docker is not installed, Docker Desktop is not running, or the Docker CLI is not available in your shell `PATH`.

Fix on macOS:

1. Install Docker Desktop from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
2. Open Docker Desktop once and wait until it says Docker is running.
3. Close and reopen Terminal.
4. Check:

```bash
docker --version
docker compose version
```

After those commands work, run the project again.

From the project root:

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
docker compose up --build
```

Open:

```text
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

## Stock Quote Mode From Free Sources

True real-time stock Level-2 order-book data is usually paid and exchange-licensed. This project now includes a free-source stock quote mode that polls a free quote API and converts the current stock price into a synthetic order book. That lets the simulator estimate stock trade costs using the existing slippage, fee, and impact pipeline.

Supported providers:

- Finnhub quote API: [https://finnhub.io/docs/api/quote](https://finnhub.io/docs/api/quote)
- Alpha Vantage Global Quote API: [https://www.alphavantage.co/documentation/](https://www.alphavantage.co/documentation/)

### Run Stock Mode With Docker

Create a free Finnhub API key, then run:

```bash
cd /Users/prabhatkumar/Downloads/algo-trade-simulator-main
export FINNHUB_API_KEY=your_finnhub_key
export STOCK_SYMBOL=AAPL
docker compose --profile stocks up --build
```

Open:

```text
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

```text
http://localhost:8050
```

Important: because free quote APIs do not provide full market depth, `stock_data_feeder.py` creates a synthetic order book around the latest quote. Use it for learning, demos, and cost-estimation experiments, not for live trading decisions.

## Hugging Face Spaces Deployment

This repository already contains a GitHub workflow that pushes to Hugging Face Spaces when code is pushed to `main`. To deploy successfully:

1. Create a Hugging Face Space using Docker SDK.
2. Add GitHub secret `HF_TOKEN` with a Hugging Face token that has write access.
3. Update `.github/workflows/sync.yml` if your Hugging Face username or Space name is different.
4. Push changes to GitHub `main`.
5. In Hugging Face Space settings, make sure the Space uses the Dockerfile.

Important note: a single Hugging Face Space container does not run Docker Compose internally. For Hugging Face, deploy the dashboard container with the root Dockerfile and use an external Redis service, or simplify to a single-container mode. For full Redis plus feeder plus load balancer, use a VM, Render Blueprint, Railway, Fly.io, AWS ECS, or any host that supports Docker Compose.

## Render / Railway / Fly Deployment Notes

For platforms that support multiple services, create these services:

- Redis service
- Web service from this Dockerfile
- Worker service running `python trading/data_feeder.py`

Environment variables for the web service and worker:

```text
REDIS_HOST=<your redis host>
REDIS_PORT=6379
PORT=7860
WEB_CONCURRENCY=2
GUNICORN_THREADS=4
WEBSOCKET_URI=wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP
```

Start command for web service:

```bash
gunicorn -b 0.0.0.0:$PORT --workers $WEB_CONCURRENCY --worker-class gthread --threads $GUNICORN_THREADS --timeout 120 trading.src.main:server
```

Start command for worker service:

```bash
python trading/data_feeder.py
```

## Testing

```bash
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 -m unittest discover trading/tests
```

Expected result:

```text
Ran 5 tests
OK
```

## Important Terms Used In This Project

- Algorithmic trading: using software rules or models to analyze and execute trades.
- Trade simulator: a tool that estimates trade execution behavior without placing real orders.
- Order book: the live list of buy and sell orders available in a market.
- Level-2 data: detailed order book data containing multiple bid and ask price levels.
- Bid: the highest price buyers are currently willing to pay.
- Ask: the lowest price sellers are currently willing to accept.
- Spread: the difference between the best ask and best bid.
- Mid price: the average of the best bid and best ask.
- Market order: an order that executes immediately against available liquidity.
- Slippage: the difference between expected execution price and actual/estimated execution price.
- Market impact: the price movement caused by placing a trade, especially a large trade.
- Fees: exchange charges paid for trade execution.
- Maker: a trader/order that adds liquidity to the order book.
- Taker: a trader/order that removes liquidity from the order book.
- Maker/taker proportion: estimated split between liquidity-adding and liquidity-removing behavior.
- Volatility: a measure of how much the asset price moves over time.
- Liquidity: how easily an asset can be bought or sold without moving the price too much.
- Order book imbalance: difference between bid and ask volume, normalized by total volume.
- Net cost: total estimated execution cost including fees, slippage, and market impact.
- Redis: an in-memory data store used here for Pub/Sub and saved trading projects.
- Pub/Sub: publish/subscribe messaging where one service publishes data and others consume it.
- WebSocket: a persistent network connection used for real-time streaming data.
- Dash: Python framework for building interactive dashboards.
- Plotly: charting library used by Dash for visualizations.
- Flask: web server framework underneath Dash.
- Gunicorn: production Python WSGI server used to run the Dash/Flask app.
- Worker: a Gunicorn process that handles web requests.
- Thread: a lightweight execution unit inside a worker.
- Load balancer: service that distributes incoming traffic across app instances.
- Nginx: reverse proxy used here as the load balancer.
- Health check: endpoint or command used to confirm a service is alive.
- Docker: container runtime used to package and run the app consistently.
- Docker Compose: tool for running multiple Docker services together.
- WSGI: Python web server interface used by Gunicorn to serve Flask/Dash.
- Environment variable: runtime configuration passed outside the code.
- Stock quote: latest reported price information for a stock symbol.
- Synthetic order book: estimated bid/ask depth generated from quote data when real Level-2 stock data is unavailable.
- API key: secret token used to access a third-party data provider.

## Common Deployment Problems And Fixes

- `zsh: command not found: docker`: install Docker Desktop, open it once, reopen Terminal, then run `docker --version`.
- `ModuleNotFoundError: No module named src`: run from the project root and use `trading.src.main:server` for Gunicorn.
- Dashboard opens but says `Not connected`: Redis or the data feeder is not running, or `REDIS_HOST` is wrong.
- Docker Compose does not work: install Docker Desktop first and make sure `docker compose version` works.
- Hugging Face build fails with Compose: Hugging Face Spaces expects a single Dockerfile container, not a multi-service compose stack.
- No market data appears: check `WEBSOCKET_URI` and whether your network can reach the WebSocket endpoint.
- Stock mode logs `API key is required`: create a free Finnhub or Alpha Vantage key and export it before starting the stock feeder.

## License

Add your preferred license before publishing the project publicly.
