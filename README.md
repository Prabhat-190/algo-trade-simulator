# Algo Trade Simulator

A real-time **transaction cost simulator**. It consumes Level-2 order book data and estimates what a market order would actually cost to execute — broken down into exchange fees, slippage and market impact — then renders the result in a live dashboard.

It is a **pre-trade cost analysis tool**. It does not place orders, connect to a broker, or backtest strategies.

```
┌──────────────┐     ┌─────────┐     ┌──────────────────────────────┐
│ Market data  │────▶│  Redis  │────▶│  Dashboard (Dash + Gunicorn) │
│  (optional   │     │(optional│     │  ┌────────────────────────┐  │
│   feeders)   │     │         │     │  │ Embedded feed fallback │  │
└──────────────┘     └─────────┘     │  └────────────────────────┘  │
                                     │   TradeSimulator → charts    │
                                     └──────────────────────────────┘
```

Both the feeders and Redis are optional. With neither, the dashboard runs its own embedded market feed, which is what makes a one-service deploy work.

---

## Quick start

```bash
git clone https://github.com/Prabhat-190/algo-trade-simulator.git
cd algo-trade-simulator

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m trading.src.main
```

Open <http://localhost:8050>. The order book populates within a second or two — no API keys, no Redis, no extra processes.

With Docker:

```bash
docker compose up --build     # http://localhost:8080
```

---

## Deploying to Railway

The repository is configured to deploy as a **single service with no add-ons**.

1. Create a project on [Railway](https://railway.app) and point it at this repository.
2. Railway reads `railway.toml`, builds the `Dockerfile` and injects `PORT` automatically.
3. Generate a public domain under **Settings → Networking**.

That is the whole process. `/healthz` is the health check and the embedded feed means the dashboard has data the moment it boots.

Using the CLI instead:

```bash
npm i -g @railway/cli
railway login
railway init
railway up
railway domain
```

### Optional upgrades

| Goal | What to add |
| --- | --- |
| Saved projects shared across replicas | Add a Railway **Redis** database. It sets `REDIS_URL`, which the app reads automatically. |
| Live exchange data instead of synthetic | Add a second service from the same repo with start command `python -m trading.data_feeder`, plus Redis. The dashboard prefers real frames automatically. |
| Live stock data | Same, with `python -m trading.stock_data_feeder` and a `FINNHUB_API_KEY`. |

No code changes are needed for any of these — only environment variables.

---

## Market data sources

`FEED_SOURCE` controls where order book frames come from.

| Value | Behaviour | Use when |
| --- | --- | --- |
| `auto` *(default)* | Subscribes to Redis, and falls back to the synthetic feed whenever no frame has arrived for `FEED_STALE_AFTER_SECONDS`. | Almost always. Correct whether or not a feeder exists. |
| `synthetic` | Always generates data in-process. | Demos, offline development, tests. |
| `websocket` | The dashboard connects directly to `WEBSOCKET_URI`. | Live data without running Redis. |
| `redis` | Redis only, no fallback. The dashboard stays empty if nothing publishes. | Multi-service deployments where silence should be visible. |

### The synthetic feed

`trading/src/data/synthetic_feed.py` generates frames in the same shape as the live exchange feed. The mid price follows a geometric Brownian motion with mild mean reversion, and depth decays exponentially away from the touch, so slippage and impact land in a believable range rather than the flat book a naive generator produces. Tune it with `SYNTHETIC_START_PRICE`, `SYNTHETIC_VOLATILITY`, `SYNTHETIC_SPREAD_BPS` and `SYNTHETIC_DEPTH`.

Because each Gunicorn worker builds its own app instance, the fallback feeds its worker in-process rather than publishing to Redis. Workers therefore never fight over synthetic frames.

---

## Cost model

For an order of size *Q* at mid price *P*, with average daily volume *V*:

**Fees** — OKX spot and futures maker/taker rates across VIP0–VIP5, blended by the estimated maker proportion.

**Slippage** — crossing the spread costs at least half of it per unit. The per-unit concession then widens with order size (logarithmically), with volatility, and narrows when the book leans in the trade's favour. The result is multiplied by *Q* to give a total cost.

**Market impact** — Almgren-Chriss, driven by the participation rate *Q/V*:

- Temporary impact follows the empirical square-root law, `Δp/p ≈ Y·σ·√(Q/V)`, widened by a bounded penalty when the order is large relative to visible depth. It reverts after execution.
- Permanent impact is linear in participation and does not revert.
- Execution risk is `0.5·ψ·σ²·T·value`.

**Maker/taker split** — logistic regression when trained weights are supplied via `MODELS_DIR`, otherwise a heuristic over size, spread, volatility and imbalance.

Both the slippage and maker/taker models accept pre-trained scikit-learn weights. Drop `slippage_model.joblib` and `maker_taker_model.joblib` into `MODELS_DIR` and they replace the heuristics at startup.

Typical output: fees dominate small orders (a $100 order costs roughly the taker fee), while market impact takes over as size grows.

---

## Configuration

Every setting has a working default. See [`.env.example`](.env.example) for the annotated list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8050` | Port to bind (`8080` in the container) |
| `LOG_LEVEL` | `INFO` | Root log level |
| `FEED_SOURCE` | `auto` | Market data source, see above |
| `SYMBOL` | `BTC-USDT` | Symbol shown in the UI and synthetic frames |
| `FEED_STALE_AFTER_SECONDS` | `6` | Silence before the embedded fallback engages |
| `REDIS_URL` | — | Managed Redis connection string; takes precedence over the host/port pair |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | Redis location when no URL is set |
| `MODELS_DIR` | — | Directory holding pre-trained `.joblib` model weights |
| `WEB_CONCURRENCY` | `2` | Gunicorn workers |
| `GUNICORN_THREADS` | `4` | Threads per worker |

Redis is never required. If it is unreachable the app logs a warning and keeps running with in-memory project storage.

---

## HTTP endpoints

| Endpoint | Purpose |
| --- | --- |
| `/` | The dashboard |
| `/healthz` | Always `200` while the process is alive. Reports Redis state, market data freshness and feed status. |
| `/readyz` | `200` only once market data has actually arrived, otherwise `503`. Use this to gate traffic. |

```bash
curl -s localhost:8050/healthz | python -m json.tool
```

---

## Project layout

```
trading/
├── data_feeder.py             # Optional service: exchange WebSocket → Redis
├── stock_data_feeder.py       # Optional service: stock quotes → synthetic book → Redis
├── examples/                  # Standalone Almgren-Chriss demo (needs matplotlib)
├── tests/                     # pytest suite
└── src/
    ├── app.py                 # create_app() factory, health routes
    ├── main.py                # Entrypoint; exposes `server` for Gunicorn
    ├── config.py              # All environment parsing
    ├── logging_config.py      # Single logging setup
    ├── data/
    │   ├── orderbook.py       # L2 book: mid, spread, depth, imbalance
    │   ├── redis_bus.py       # Shared connect / publish / subscribe helpers
    │   ├── synthetic_feed.py  # Embedded market data generator
    │   └── websocket_client.py# Reconnecting WebSocket client
    ├── models/
    │   ├── simulator.py       # TradeSimulator: orchestrates the cost models
    │   ├── fee_model.py       # Exchange fee tiers
    │   ├── slippage_model.py  # Slippage regression + heuristic fallback
    │   ├── market_impact.py   # Almgren-Chriss impact and execution schedule
    │   ├── maker_taker.py     # Maker/taker split
    │   └── trading_project.py # Saved simulation setups
    ├── services/
    │   ├── feed_manager.py    # Owns the background data threads
    │   └── market_state.py    # Thread-safe access to the simulator
    ├── ui/
    │   ├── dashboard.py       # Dash app assembly
    │   ├── layout.py          # Component tree
    │   ├── callbacks.py       # Callback registration
    │   ├── figures.py         # Plotly chart builders
    │   └── assets/theme.css   # Dark glassmorphic theme
    └── visualization/         # Static matplotlib plots (demo only)
```

Order book frames arrive on background threads while Dash callbacks read the same simulator from request threads. All access goes through `MarketState`, which holds a lock, so a callback can never observe a half-applied book.

---

## Development

```bash
pip install -r requirements-dev.txt

pytest                  # 108 tests
ruff check .            # lint
ruff check --fix .      # autofix
```

CI runs lint and tests on Python 3.11 and 3.12, then builds the image and asserts that a bare container reaches `/readyz` with no Redis and no API keys.

`matplotlib` lives in `requirements-dev.txt` because only `trading/examples/` and `trading/src/visualization/` use it. Keeping it out of `requirements.txt` makes the production image meaningfully smaller.

### Running the optional feeders locally

```bash
docker compose --profile live up      # Redis + crypto WebSocket feeder + dashboard
docker compose --profile stocks up    # Redis + stock feeder + dashboard

# or directly
python -m trading.data_feeder
python -m trading.stock_data_feeder --symbol AAPL
```

---

## License

MIT
